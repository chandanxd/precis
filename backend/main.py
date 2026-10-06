"""
Précis: API Server
FastAPI application exposing the NLP pipeline as REST + WebSocket endpoints.
"""

import asyncio
import os
import time
from collections.abc import Callable, Generator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from precis.api.models import (
    DocumentInfo,
    DocumentListResponse,
    HardwareResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    StatsResponse,
    TokenResponse,
)
from precis.api.security import (
    JWTMiddleware,
    check_injection,
    generate_token,
    query_limiter,
    sanitize_document,
    sanitize_query,
    validate_token,
)
from precis.graph.store import FactStore
from precis.pipeline.hardware import HardwareProfile, profile_hardware
from precis.pipeline.inference import (
    OllamaConnectionError,
    OllamaInferenceError,
    generate_answer,
)
from precis.pipeline.orchestrator import (
    ingest_document as run_ingest_document,
)
from precis.pipeline.orchestrator import (
    query_pipeline,
)
from precis.pipeline.packer import pack_context, render_context

# Global application state
store: FactStore | None = None
hardware: HardwareProfile | None = None


CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "PRECIS_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
    ).split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize persistent fact store and hardware profile on startup."""
    global store, hardware

    data_dir = os.getenv("PRECIS_DATA_DIR", "./chroma_data")
    store = FactStore(persist_dir=data_dir)
    hardware = profile_hardware()

    print(
        "Précis API started. "
        f"Hardware profile: {hardware.recommended_model} "
        f"({hardware.token_ceiling} token ceiling)"
    )

    yield

    print("Précis API shutting down.")


app = FastAPI(
    title="Précis",
    description="Epistemically-typed SVOA compression for CPU-viable edge RAG",
    version="0.1.0",
    lifespan=lifespan,
)

# Zero-trust JWT verification middleware
app.add_middleware(JWTMiddleware)

# CORS middleware for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_store() -> FactStore:
    global store

    if store is None:
        data_dir = os.getenv("PRECIS_DATA_DIR", "./chroma_data")
        store = FactStore(persist_dir=data_dir)

    return store


def _get_hardware() -> HardwareProfile:
    global hardware

    if hardware is None:
        hardware = profile_hardware()

    return hardware


def _next_stream_item(
    stream_gen: Generator[str, None, Any],
) -> tuple[bool, str | Any]:
    """
    Advance a synchronous generator without exposing StopIteration.

    Returning an explicit completion flag prevents StopIteration from being
    propagated through asyncio.Future, where it cannot be used as a result.
    """
    try:
        return True, next(stream_gen)
    except StopIteration as exc:
        return False, exc.value


async def _stream_generator(
    stream_gen: Generator[str, None, Any],
    on_token: Callable[[str], Any],
) -> Any:
    """Consume a synchronous generator without blocking the event loop."""
    while True:
        has_token, value = await asyncio.to_thread(
            _next_stream_item,
            stream_gen,
        )

        if not has_token:
            return value

        await on_token(value)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/auth/token", response_model=TokenResponse)
async def get_token() -> TokenResponse:
    """Generate a JWT bearer token for API access."""
    token = generate_token()

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=24 * 3600,
    )


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest_document(req: IngestRequest) -> IngestResponse:
    """
    Ingest a document:
    1. Sanitize text & check for prompt injection
    2. Neural coreference resolution (Stage 1)
    3. SVOA extraction with negation & modality typing (Stage 2)
    4. 4-term SDH scoring & vector indexing (Stage 3)
    """
    try:
        clean_text = sanitize_document(req.text)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not clean_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Document text cannot be empty",
        )

    if check_injection(clean_text):
        raise HTTPException(
            status_code=400,
            detail="Input rejected: suspicious content detected",
        )

    document_name = (req.document_name.strip() or "document")[:255]
    active_store = _get_store()

    try:
        result = await asyncio.to_thread(
            run_ingest_document,
            text=clean_text,
            source_doc=document_name,
            store=active_store,
        )
    except Exception as exc:
        print(f"Document ingestion failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed.",
        ) from exc

    return IngestResponse(
        document_name=result.document_name,
        facts_extracted=result.facts_extracted,
        facts_stored=result.facts_stored,
        latency_ms=result.latency_ms,
    )


@app.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest, request: Request) -> QueryResponse:
    """
    Query ingested knowledge base:
    1. Check sliding-window rate limit (10 req/min)
    2. Sanitize query & check prompt injection
    3. Query-adaptive re-ranking & modality packing (Stage 4)
    4. Local LLM inference via Ollama (Stage 5)
    """
    client_ip = request.client.host if request.client else "127.0.0.1"

    if not query_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Max 10 queries per minute.",
            headers={"Retry-After": "60"},
        )

    try:
        clean_query = sanitize_query(req.question)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not clean_query.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty",
        )

    if check_injection(clean_query):
        raise HTTPException(
            status_code=400,
            detail="Input rejected: suspicious content detected",
        )

    active_store = _get_store()
    active_hardware = _get_hardware()

    if active_store.count() == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents ingested. Upload a document first.",
        )

    t0 = time.perf_counter()
    selected_model = active_hardware.recommended_model
    inf_tokens = 0

    try:
        pipeline_res = await asyncio.to_thread(
            query_pipeline,
            query=clean_query,
            store=active_store,
            hardware=active_hardware,
            model=active_hardware.recommended_model,
            stream=False,
        )
        answer = pipeline_res.answer
        packed_facts = pipeline_res.facts_used
        tokens_used = pipeline_res.tokens_used
        naive_rag_tokens = pipeline_res.naive_rag_tokens
        compression_rate = pipeline_res.compression_rate
        avg_sdh_score = pipeline_res.avg_sdh_score
        elapsed_ms = pipeline_res.latency_ms
        selected_model = pipeline_res.model or selected_model
        inf_tokens = pipeline_res.inference_tokens

    except OllamaConnectionError:
        # Fallback when Ollama service is not running on localhost.
        if os.getenv("PRECIS_MOCK_OLLAMA") == "1" or not os.getenv(
            "PRECIS_STRICT_OLLAMA"
        ):
            pack = pack_context(
                clean_query,
                active_store,
                active_hardware.token_ceiling,
            )
            facts_summary = "; ".join(
                f"{fact.subject} "
                f"{'NOT ' if fact.negated else ''}"
                f"{fact.verb} {fact.object}"
                for fact in pack.packed_facts[:3]
            )
            answer = (
                "Based on the extracted facts: "
                f"{facts_summary or 'No relevant facts found'}."
            )
            packed_facts = pack.packed_facts
            tokens_used = pack.tokens_used
            naive_rag_tokens = pack.naive_rag_tokens
            compression_rate = pack.compression_rate
            avg_sdh_score = pack.avg_sdh_score
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
        else:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Ollama service is unreachable. Ensure 'ollama serve' is running."
                ),
            )

    except OllamaInferenceError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Local inference failed: {exc}",
        ) from exc

    facts_payload = [
        {
            "subject": fact.subject,
            "verb": fact.verb,
            "object": fact.object,
            "negated": fact.negated,
            "modality": fact.modality,
            "sdh_score": fact.sdh_score,
            "adjuncts": fact.adjuncts,
            "attributed_to": fact.attributed_to,
        }
        for fact in packed_facts
    ]

    return QueryResponse(
        answer=answer,
        facts_used=facts_payload,
        tokens_used=tokens_used,
        naive_rag_tokens=naive_rag_tokens,
        compression_rate=compression_rate,
        avg_sdh_score=avg_sdh_score,
        latency_ms=elapsed_ms,
        model=selected_model,
        inference_tokens=inf_tokens,
    )


@app.get("/api/hardware", response_model=HardwareResponse)
async def get_hardware() -> HardwareResponse:
    """Return calibrated hardware profile and token ceilings."""
    profile = _get_hardware()
    return HardwareResponse(**profile.to_dict())


@app.get("/api/facts/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """Return comprehensive summary metrics regarding stored facts."""
    active_store = _get_store()
    raw_stats = active_store.stats()

    return StatsResponse(
        total_facts=raw_stats.get("total_facts", 0),
        negated_count=raw_stats.get("negated_count", 0),
        modality_breakdown=raw_stats.get("modality_breakdown", {}),
        avg_sdh_score=raw_stats.get("avg_sdh_score", 0.0),
    )


@app.get("/api/documents", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """List all ingested documents and their fact counts."""
    active_store = _get_store()

    if active_store.count() == 0:
        return DocumentListResponse(documents=[])

    all_results = active_store.collection.get(include=["metadatas"])
    metadatas = all_results.get("metadatas") or []

    doc_counts: dict[str, int] = {}

    for metadata in metadatas:
        source_doc = metadata.get("source_doc")
        if isinstance(source_doc, str) and source_doc:
            doc = source_doc
        else:
            doc = "unknown"
        doc_counts[doc] = doc_counts.get(doc, 0) + 1

    return DocumentListResponse(
        documents=[
            DocumentInfo(name=name, fact_count=count)
            for name, count in sorted(doc_counts.items())
        ]
    )


@app.delete("/api/facts")
async def clear_facts() -> dict[str, Any]:
    """Clear all facts from the store."""
    active_store = _get_store()
    deleted = active_store.clear()

    return {
        "deleted": deleted,
        "status": "cleared",
    }


@app.delete("/api/documents/{doc_name}")
async def delete_document(
    doc_name: str = PathParam(
        ...,
        description="Document name to delete",
    ),
) -> dict[str, Any]:
    """Delete all facts belonging to a specific document."""
    document_name = doc_name.strip()

    if not document_name:
        raise HTTPException(
            status_code=400,
            detail="Document name cannot be empty",
        )

    active_store = _get_store()
    deleted = active_store.delete_document(document_name)

    if deleted == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_name}' not found",
        )

    return {
        "document": document_name,
        "deleted": deleted,
    }


# --- WebSocket Live Pipeline Event Streaming ---


class ConnectionManager:
    """Manage active WebSocket connections."""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def send_json(
        self,
        ws: WebSocket,
        data: dict[str, Any],
    ) -> None:
        await ws.send_json(data)

    async def broadcast(self, data: dict[str, Any]) -> None:
        disconnected: list[WebSocket] = []

        for ws in list(self.active):
            try:
                await ws.send_json(data)
            except WebSocketDisconnect as exc:
                print(f"WebSocket broadcast failed: {exc}")
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)


ws_manager = ConnectionManager()


async def _handle_ws_query(
    ws: WebSocket,
    data: dict[str, Any],
) -> None:
    """Handle a query over WebSocket with real-time token streaming."""
    client_ip = ws.client.host if ws.client else "127.0.0.1"
    if not query_limiter.is_allowed(client_ip):
        await ws.send_json(
            {
                "type": "error",
                "detail": "Rate limit exceeded. Max 10 queries per minute.",
            }
        )
        return

    question = data.get("question", "")
    try:
        clean_question = sanitize_query(question)
    except ValueError as exc:
        await ws.send_json(
            {
                "type": "error",
                "detail": str(exc),
            }
        )
        return

    if not clean_question.strip():
        await ws.send_json(
            {
                "type": "error",
                "detail": "Empty question",
            }
        )
        return

    if check_injection(clean_question):
        await ws.send_json(
            {
                "type": "error",
                "detail": "Suspicious content detected",
            }
        )
        return

    active_store = _get_store()
    active_hardware = _get_hardware()

    if active_store.count() == 0:
        await ws.send_json(
            {
                "type": "error",
                "detail": "No documents ingested",
            }
        )
        return

    # Stage 4: Re-rank + pack
    await ws.send_json(
        {
            "type": "pipeline:stage",
            "payload": {
                "stage": 4,
                "stage_name": "Re-rank + pack",
                "status": "running",
                "detail": "Packing context...",
            },
        }
    )

    t0_pack = time.perf_counter()

    pack = await asyncio.to_thread(
        pack_context,
        clean_question,
        active_store,
        active_hardware.token_ceiling,
    )
    context = render_context(pack.packed_facts)

    pack_ms = int((time.perf_counter() - t0_pack) * 1000)

    await ws.send_json(
        {
            "type": "pipeline:stage",
            "payload": {
                "stage": 4,
                "stage_name": "Re-rank + pack",
                "status": "complete",
                "detail": (
                    f"{pack.tokens_used} tokens | "
                    f"{pack.compression_rate:.1%} compression | "
                    f"{pack.facts_packed} facts"
                ),
                "count": pack.facts_packed,
                "latency_ms": pack_ms,
            },
        }
    )

    # Stage 5: Inference
    await ws.send_json(
        {
            "type": "pipeline:stage",
            "payload": {
                "stage": 5,
                "stage_name": "LLM inference",
                "status": "running",
                "detail": (f"{active_hardware.recommended_model} generating..."),
            },
        }
    )

    full_answer: list[str] = []
    inference_result = None
    t0_inf = time.perf_counter()

    async def send_token(token: str) -> None:
        """Send one streamed token to the WebSocket client."""
        full_answer.append(token)

        await ws.send_json(
            {
                "type": "pipeline:token",
                "payload": {"char": token},
            }
        )

        await asyncio.sleep(0)

    try:
        stream_gen = generate_answer(
            query=clean_question,
            context=context,
            model=active_hardware.recommended_model,
            stream=True,
        )

        inference_result = await _stream_generator(
            stream_gen,
            send_token,
        )

    except OllamaConnectionError:
        if os.getenv("PRECIS_MOCK_OLLAMA") == "1" or not os.getenv(
            "PRECIS_STRICT_OLLAMA"
        ):
            fallback_msg = (
                f"Extracted facts for query: {render_context(pack.packed_facts[:2])}"
            )

            for word in fallback_msg.split(" "):
                token = word + " "
                full_answer.append(token)

                await ws.send_json(
                    {
                        "type": "pipeline:token",
                        "payload": {"char": token},
                    }
                )

                await asyncio.sleep(0.01)
        else:
            await ws.send_json(
                {
                    "type": "error",
                    "detail": (
                        "Ollama service is unreachable. Ensure 'ollama serve' is running."
                    ),
                }
            )
            return

    except OllamaInferenceError as exc:
        await ws.send_json(
            {
                "type": "error",
                "detail": f"Local inference failed: {exc}",
            }
        )
        return

    inference_ms = int((time.perf_counter() - t0_inf) * 1000)
    total_latency_ms = int((time.perf_counter() - t0_pack) * 1000)

    generated_tokens = (
        inference_result.tokens_generated
        if inference_result is not None
        else len(full_answer)
    )

    await ws.send_json(
        {
            "type": "pipeline:stage",
            "payload": {
                "stage": 5,
                "stage_name": "LLM inference",
                "status": "complete",
                "detail": (
                    f"{active_hardware.recommended_model} | "
                    f"{inference_ms}ms | "
                    f"{generated_tokens} tokens"
                ),
                "count": generated_tokens,
                "latency_ms": inference_ms,
            },
        }
    )

    await ws.send_json(
        {
            "type": "pipeline:done",
            "payload": {
                "answer": "".join(full_answer).strip(),
                "facts_used": [
                    {
                        "subject": fact.subject,
                        "verb": fact.verb,
                        "object": fact.object,
                        "negated": fact.negated,
                        "modality": fact.modality,
                        "sdh_score": fact.sdh_score,
                        "adjuncts": fact.adjuncts,
                        "attributed_to": fact.attributed_to,
                    }
                    for fact in pack.packed_facts
                ],
                "tokens_used": pack.tokens_used,
                "naive_rag_tokens": pack.naive_rag_tokens,
                "compression_rate": pack.compression_rate,
                "avg_sdh_score": pack.avg_sdh_score,
                "latency_ms": total_latency_ms,
                "model": active_hardware.recommended_model,
                "inference_tokens": generated_tokens,
            },
        }
    )


async def _handle_ws_ingest(
    ws: WebSocket,
    data: dict[str, Any],
) -> None:
    """Handle document ingestion with pipeline events over WebSocket."""
    text = data.get("text", "")
    doc_name = (str(data.get("document_name", "document")).strip() or "document")[:255]

    try:
        clean_text = sanitize_document(text)
    except ValueError as exc:
        await ws.send_json(
            {
                "type": "error",
                "detail": str(exc),
            }
        )
        return

    if not clean_text.strip():
        await ws.send_json(
            {
                "type": "error",
                "detail": "Empty document",
            }
        )
        return

    if check_injection(clean_text):
        await ws.send_json(
            {
                "type": "error",
                "detail": "Suspicious content detected",
            }
        )
        return

    active_store = _get_store()

    stages = [
        (0, "Hardware detection"),
        (1, "Coreference resolution"),
        (2, "SVOA extraction"),
        (3, "SDH scoring & storage"),
    ]

    for stage_num, stage_name in stages:
        await ws.send_json(
            {
                "type": "pipeline:stage",
                "payload": {
                    "stage": stage_num,
                    "stage_name": stage_name,
                    "status": "running",
                    "detail": f"{stage_name}...",
                },
            }
        )

    t0 = time.perf_counter()

    try:
        result = await asyncio.to_thread(
            run_ingest_document,
            text=clean_text,
            source_doc=doc_name,
            store=active_store,
        )
    except WebSocketDisconnect as exc:
        print(f"Document ingestion failed: {exc}")

        await ws.send_json(
            {
                "type": "error",
                "detail": "Document ingestion failed",
            }
        )
        return

    total_ms = int((time.perf_counter() - t0) * 1000)

    for stage_num, stage_name in stages:
        await ws.send_json(
            {
                "type": "pipeline:stage",
                "payload": {
                    "stage": stage_num,
                    "stage_name": stage_name,
                    "status": "complete",
                    "detail": f"{stage_name} complete",
                },
            }
        )

    await ws.send_json(
        {
            "type": "ingest:done",
            "payload": {
                "document_name": result.document_name,
                "facts_extracted": result.facts_extracted,
                "facts_stored": result.facts_stored,
                "latency_ms": total_ms,
            },
        }
    )


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Real-time bidirectional WebSocket connection for pipeline events and tokens."""
    authenticated = False
    auth_token = ws.query_params.get("token")
    if not auth_token:
        auth_header = ws.headers.get("authorization") or ws.headers.get("Authorization")
        if auth_header:
            auth_token = (
                auth_header[7:].strip()
                if auth_header.startswith("Bearer ")
                else auth_header.strip()
            )

    if auth_token:
        try:
            validate_token(auth_token)
            authenticated = True
        except HTTPException:
            authenticated = False

    await ws_manager.connect(ws)

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await ws.send_json({"type": "pong"})
                continue

            if msg_type == "auth":
                token_to_verify = data.get("token") or ""
                try:
                    validate_token(token_to_verify)
                    authenticated = True
                    await ws.send_json(
                        {
                            "type": "auth_ok",
                            "detail": "Authenticated successfully.",
                        }
                    )
                except HTTPException:
                    authenticated = False
                    await ws.send_json(
                        {
                            "type": "error",
                            "detail": "Invalid or expired token.",
                        }
                    )
                continue

            if not authenticated:
                payload_token = data.get("token")
                if payload_token:
                    try:
                        validate_token(payload_token)
                        authenticated = True
                    except HTTPException:
                        authenticated = False

            if not authenticated:
                await ws.send_json(
                    {
                        "type": "error",
                        "detail": "Authentication required. Provide a valid token.",
                    }
                )
                continue

            if msg_type == "query":
                await _handle_ws_query(ws, data)

            elif msg_type == "ingest":
                await _handle_ws_ingest(ws, data)

            else:
                await ws.send_json(
                    {
                        "type": "unknown_command",
                        "detail": f"Unrecognized type: {msg_type}",
                    }
                )

    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
