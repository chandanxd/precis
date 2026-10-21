"""
Précis: API Server
FastAPI application exposing the NLP pipeline as REST + WebSocket endpoints.
"""

import asyncio
import json
import os
import re
import threading
import time
from pathlib import Path
from collections.abc import Callable, Generator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi import Path as PathParam
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
from precis.api.models import (
    DocumentInfo,
    DocumentListResponse,
    FactListResponse,
    HardwareResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    StatsResponse,
    TokenRequest,
    TokenResponse,
)
from precis.api.security import (
    DEFAULT_USER,
    JWTMiddleware,
    check_injection,
    generate_token,
    is_client_id,
    query_limiter,
    sanitize_document,
    sanitize_document_layout,
    sanitize_query,
    validate_token,
    verify_mint_key,
)
from precis.graph.store import FactStore
from precis.pipeline.hardware import HardwareProfile, profile_hardware
from precis.pipeline.history import session_manager
from precis.pipeline.inference import (
    OllamaConnectionError,
    OllamaInferenceError,
    generate_answer,
)
from precis.pipeline.orchestrator import (
    assemble_query_context,
    ingest_document as run_ingest_document,
    query_pipeline,
    route_chat_query,
)
from precis.pipeline.packer import pack_context, render_context
from precis.pipeline.routing import QueryIntent, classify_query_intent
from precis.pipeline.structural import is_list_extraction_enabled


# Global application state
store: FactStore | None = None
hardware: HardwareProfile | None = None


CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "PRECIS_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize persistent fact store and hardware profile on startup."""
    global store, hardware

    data_dir = os.getenv("PRECIS_DATA_DIR", DEFAULT_DATA_DIR)
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


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def _mock_ollama_allowed() -> bool:
    """Whether canned answers may stand in for an unreachable Ollama."""
    return _env_flag("PRECIS_MOCK_OLLAMA") or not _env_flag("PRECIS_STRICT_OLLAMA")


_MODEL_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}$")
_MODALITIES = {"asserted", "attributed", "conditional", "hypothetical"}


def _parse_query_options(raw: Any) -> dict[str, Any]:
    """Validate optional per-query settings sent by the client.

    Unknown keys and invalid values are ignored; only the safe, bounded subset
    below is ever applied.
    """
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}

    model = raw.get("model")
    if isinstance(model, str) and _MODEL_TAG.match(model):
        out["model"] = model

    ceiling = raw.get("token_ceiling")
    if isinstance(ceiling, (int, float)) and not isinstance(ceiling, bool):
        out["token_ceiling"] = max(256, min(int(ceiling), 8192))

    temperature = raw.get("temperature")
    if isinstance(temperature, (int, float)) and not isinstance(temperature, bool):
        if 0.0 <= temperature <= 2.0:
            out["temperature"] = float(temperature)

    allowed = raw.get("allowed_modalities")
    if isinstance(allowed, list) and all(isinstance(m, str) for m in allowed):
        enabled = _MODALITIES & set(allowed)
        # Never allow an empty selection to silently drop all evidence.
        if enabled:
            out["exclude_modalities"] = _MODALITIES - enabled or None

    return out


def _has_documents(active_store: FactStore) -> bool:
    """Blocking check for any ingested content; call via asyncio.to_thread."""
    if active_store.count() > 0:
        return True
    return bool(
        is_list_extraction_enabled()
        and hasattr(active_store, "has_structural_evidence")
        and active_store.has_structural_evidence()
    )


def _get_store() -> FactStore:
    global store

    if store is None:
        data_dir = os.getenv("PRECIS_DATA_DIR", DEFAULT_DATA_DIR)
        store = FactStore(persist_dir=data_dir)

    return store


# Resolved against this file, not the working directory, so the same data is
# found however the server is launched.
DEFAULT_DATA_DIR = str(Path(__file__).resolve().parent / "chroma_data")

_user_stores: dict[str, FactStore] = {}
_user_stores_lock = threading.Lock()


def _store_for(user_sub: str) -> FactStore:
    """Fact store for a user.

    Browser clients (client-<hex> subjects) each get their own collections in
    the shared persistent database. Every other subject, including the default
    one used before client IDs existed, uses the original shared store.
    """
    if not is_client_id(user_sub):
        return _get_store()
    with _user_stores_lock:
        user_store = _user_stores.get(user_sub)
        if user_store is None:
            data_dir = os.getenv("PRECIS_DATA_DIR", DEFAULT_DATA_DIR)
            user_store = FactStore(
                persist_dir=data_dir,
                collection_name=f"facts_u_{user_sub[len('client-'):]}",
            )
            _user_stores[user_sub] = user_store
        return user_store


def _user_of(request: Request) -> str:
    return getattr(request.state, "user_sub", DEFAULT_USER)


def _session_key(user_sub: str, session_id: str | None) -> str | None:
    """Namespace a chat session by user so IDs cannot collide across users."""
    if not session_id or user_sub == DEFAULT_USER:
        return session_id
    return f"{user_sub}:{session_id}"


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
    try:
        while True:
            has_token, value = await asyncio.to_thread(
                _next_stream_item,
                stream_gen,
            )

            if not has_token:
                return value

            await on_token(value)
    finally:
        # Runs on client disconnect or error too, so the upstream Ollama
        # connection is released instead of generating into the void.
        close = getattr(stream_gen, "close", None)
        if close is not None:
            close()


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/auth/token", response_model=TokenResponse)
async def get_token(
    request: Request, body: TokenRequest | None = None
) -> TokenResponse:
    """Generate a JWT bearer token for API access.

    If PRECIS_TOKEN_MINT_KEY is set, callers must send it in X-Precis-Mint-Key.
    """
    if not verify_mint_key(request.headers.get("X-Precis-Mint-Key")):
        raise HTTPException(status_code=403, detail="Token minting is restricted")

    subject = body.client_id if body and is_client_id(body.client_id) else DEFAULT_USER
    token = generate_token(subject)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=24 * 3600,
    )


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest_document(req: IngestRequest, request: Request) -> IngestResponse:
    """
    Ingest a document:
    1. Sanitize text & check for prompt injection
    2. Neural coreference resolution (Stage 1)
    3. SVOA extraction with negation & modality typing (Stage 2)
    4. 4-term SDH scoring & vector indexing (Stage 3)
    """
    try:
        clean_text = sanitize_document(req.text)
        raw_layout = sanitize_document_layout(req.text)
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
    active_store = _store_for(_user_of(request))

    try:
        result = await asyncio.to_thread(
            run_ingest_document,
            text=clean_text,
            source_doc=document_name,
            store=active_store,
            hardware=_get_hardware(),
            raw_document=raw_layout,
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
    # Browser clients are limited individually; behind a reverse proxy every
    # request shares one IP, which would otherwise pool all users together.
    limit_key = _user_of(request) if is_client_id(_user_of(request)) else client_ip

    if not query_limiter.is_allowed(limit_key):
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

    user_sub = _user_of(request)
    active_store = _store_for(user_sub)
    active_hardware = _get_hardware()

    has_docs = await asyncio.to_thread(_has_documents, active_store)

    session_key = _session_key(user_sub, req.session_id)
    history = session_manager.get_history(session_key) if session_key else []
    intent = classify_query_intent(clean_query, has_documents=has_docs, conversation_history=history)

    if not has_docs and intent not in (QueryIntent.CONVERSATIONAL, QueryIntent.GENERAL_KNOWLEDGE):
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
            session_id=session_key,
            chat=True,
        )
        answer = pipeline_res.answer
        answer_source = pipeline_res.answer_source
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
        if _mock_ollama_allowed():
            answer_source = (
                "document"
                if intent in (QueryIntent.DOCUMENT_GROUNDED, QueryIntent.AMBIGUOUS)
                else "conversation"
            )
            if answer_source == "conversation":
                answer = "Hello! I am Précis. (Local Ollama service offline mock mode)"
                packed_facts = []
                tokens_used = 0
                naive_rag_tokens = 0
                compression_rate = 0.0
                avg_sdh_score = 0.0
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
            else:
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
        session_id=req.session_id,
        answer_source=answer_source,
    )


@app.get("/api/hardware", response_model=HardwareResponse)
async def get_hardware() -> HardwareResponse:
    """Return calibrated hardware profile and token ceilings."""
    profile = _get_hardware()
    return HardwareResponse(**profile.to_dict())


@app.get("/api/facts/stats", response_model=StatsResponse)
async def get_stats(request: Request) -> StatsResponse:
    """Return comprehensive summary metrics regarding stored facts."""
    active_store = _store_for(_user_of(request))
    raw_stats = await asyncio.to_thread(active_store.stats)

    return StatsResponse(
        total_facts=raw_stats.get("total_facts", 0),
        negated_count=raw_stats.get("negated_count", 0),
        modality_breakdown=raw_stats.get("modality_breakdown", {}),
        avg_sdh_score=raw_stats.get("avg_sdh_score", 0.0),
    )


@app.get("/api/documents", response_model=DocumentListResponse)
async def list_documents(request: Request) -> DocumentListResponse:
    """List all ingested documents and their fact counts."""
    active_store = _store_for(_user_of(request))

    def _load() -> tuple[list[Any], list[str]]:
        metas: list[Any] = []
        if active_store.count() > 0:
            res = active_store.collection.get(include=["metadatas"])
            metas = list(res.get("metadatas") or [])
        structural = (
            active_store.get_structural_documents()
            if hasattr(active_store, "get_structural_documents")
            else []
        )
        return metas, structural

    metadatas, structural_docs = await asyncio.to_thread(_load)

    doc_counts: dict[str, int] = {}
    # Documents that only produced structural evidence (lists/tables) still exist.
    for name in structural_docs:
        doc_counts[name] = 0

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


@app.get("/api/facts", response_model=FactListResponse)
async def list_facts(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    source_doc: str | None = None,
) -> FactListResponse:
    """List stored facts with optional filtering by document and limit."""
    active_store = _store_for(_user_of(request))

    def _load_facts() -> list[Any]:
        if active_store.count() == 0:
            return []
        if source_doc:
            return active_store.get_by_document(source_doc, limit=limit)
        results = active_store.collection.get(
            include=["metadatas"],
            limit=limit,
        )
        metadatas = results.get("metadatas") or []
        facts = [
            active_store._metadata_to_fact(m)
            for m in metadatas
        ] if hasattr(active_store, "_metadata_to_fact") else []
        if not facts and metadatas:
            from precis.graph.store import _metadata_to_fact
            facts = [_metadata_to_fact(m) for m in metadatas]
        return facts

    def _count_total() -> int:
        if source_doc:
            found = active_store.collection.get(where={"source_doc": source_doc}, include=[])
            return len(found.get("ids") or [])
        return active_store.count()

    facts = await asyncio.to_thread(_load_facts)
    total = await asyncio.to_thread(_count_total)

    fact_payloads = [
        {
            "subject": f.subject,
            "verb": f.verb,
            "object": f.object,
            "adjuncts": f.adjuncts,
            "negated": f.negated,
            "modality": f.modality,
            "attributed_to": f.attributed_to,
            "disjunctive": f.disjunctive,
            "sdh_score": f.sdh_score,
            "source_doc": f.source_doc,
            "sentence_id": f.sentence_id,
            "original_sentence": f.raw_sentence,
        }
        for f in facts
    ]

    return FactListResponse(facts=fact_payloads, total=total)


@app.delete("/api/facts")
async def clear_facts(request: Request) -> dict[str, Any]:
    """Clear all facts from the store."""
    active_store = _store_for(_user_of(request))
    deleted = await asyncio.to_thread(active_store.clear)

    return {
        "deleted": deleted,
        "status": "cleared",
    }


@app.delete("/api/documents/{doc_name:path}")
async def delete_document(
    request: Request,
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

    active_store = _store_for(_user_of(request))

    def _delete() -> tuple[int, bool]:
        had = hasattr(
            active_store, "has_structural_evidence"
        ) and active_store.has_structural_evidence(document_name)
        return active_store.delete_document(document_name), had

    deleted, had_structural = await asyncio.to_thread(_delete)

    if deleted == 0 and not had_structural:
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
    user_sub: str = DEFAULT_USER,
) -> None:
    """Handle a query over WebSocket with real-time token streaming."""
    client_ip = ws.client.host if ws.client else "127.0.0.1"
    limit_key = user_sub if is_client_id(user_sub) else client_ip
    if not query_limiter.is_allowed(limit_key):
        await ws.send_json(
            {
                "type": "error",
                "detail": "Rate limit exceeded. Max 10 queries per minute.",
            }
        )
        return

    question = data.get("question", "")
    if not isinstance(question, str):
        await ws.send_json({"type": "error", "detail": "Question must be a string"})
        return
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

    active_store = _store_for(user_sub)
    active_hardware = _get_hardware()

    has_docs = await asyncio.to_thread(_has_documents, active_store)

    session_id = data.get("session_id")
    if not isinstance(session_id, str) or not session_id or len(session_id) > 128:
        session_id = None
    options = _parse_query_options(data.get("options"))
    effective_model = options.get("model", active_hardware.recommended_model)
    effective_ceiling = options.get("token_ceiling", active_hardware.token_ceiling)
    session_key = _session_key(user_sub, session_id)
    history = session_manager.get_history(session_key) if session_key else []
    route = await asyncio.to_thread(
        route_chat_query,
        clean_question,
        active_store,
        has_docs,
        history,
        effective_model,
    )

    if not has_docs and route.answer_source == "document":
        await ws.send_json(
            {
                "type": "error",
                "detail": "No documents ingested",
            }
        )
        return

    is_conversational = route.answer_source != "document"

    t0_pack = time.perf_counter()

    if is_conversational:
        context = ""
        assembled_facts_used: list[Any] = []
        tokens_used = 0
        naive_rag_tokens = 0
        compression_rate = 0.0
        avg_sdh_score = 0.0
        prompt_type = "conversational"
    else:
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

        assembled = await asyncio.to_thread(
            assemble_query_context,
            query=route.retrieval_query,
            store=active_store,
            token_ceiling=effective_ceiling,
            exclude_modalities=options.get("exclude_modalities"),
        )
        context = assembled.context
        assembled_facts_used = assembled.facts_used
        tokens_used = assembled.tokens_used
        naive_rag_tokens = assembled.naive_rag_tokens
        compression_rate = assembled.compression_rate
        avg_sdh_score = assembled.avg_sdh_score
        prompt_type = "document_chat"

        pack_ms = int((time.perf_counter() - t0_pack) * 1000)

        await ws.send_json(
            {
                "type": "pipeline:stage",
                "payload": {
                    "stage": 4,
                    "stage_name": "Re-rank + pack",
                    "status": "complete",
                    "detail": (
                        f"{assembled.tokens_used} tokens | "
                        f"{assembled.compression_rate:.1%} compression | "
                        f"{assembled.facts_packed} facts"
                    ),
                    "count": assembled.facts_packed,
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
                "detail": (f"{effective_model} generating..."),
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
            model=effective_model,
            stream=True,
            prompt_type=prompt_type,
            history=history,
            **({"temperature": options["temperature"]} if "temperature" in options else {}),
        )

        inference_result = await _stream_generator(
            stream_gen,
            send_token,
        )

    except OllamaConnectionError:
        if _mock_ollama_allowed():
            if is_conversational:
                fallback_msg = "Hello! I am Précis. (Local Ollama offline mock mode)"
            else:
                fallback_msg = (
                    f"Extracted facts for query: {render_context(assembled_facts_used[:2])}"
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

    final_answer_text = "".join(full_answer).strip()

    # If the ThinkBlockFilter suppressed every streamed token (model wrapped
    # its entire response in <think>…</think>), fall back to the cleaned text
    # that _stream_ollama already computed via strip_thinking_tags.
    if not final_answer_text and inference_result is not None and isinstance(getattr(inference_result, "answer", None), str):
        final_answer_text = inference_result.answer

    if not final_answer_text.strip() and assembled_facts_used:
        fact_summaries = [f"• {f.subject} {f.verb} {f.object}" for f in assembled_facts_used[:3]]
        final_answer_text = "Based on the retrieved document facts:\n" + "\n".join(fact_summaries)

    if session_key:
        session_manager.add_message(session_key, "user", clean_question)
        session_manager.add_message(
            session_key,
            "assistant",
            final_answer_text,
            grounded=not is_conversational,
        )

    await ws.send_json(
        {
            "type": "pipeline:stage",
            "payload": {
                "stage": 5,
                "stage_name": "LLM inference",
                "status": "complete",
                "detail": (
                    f"{effective_model} | "
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
                "answer": final_answer_text,
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
                        "disjunctive": getattr(fact, "disjunctive", False),
                        "source_doc": getattr(fact, "source_doc", ""),
                        "sentence_id": getattr(fact, "sentence_id", 0),
                        "original_sentence": getattr(fact, "raw_sentence", ""),
                    }
                    for fact in assembled_facts_used
                ],
                "tokens_used": tokens_used,
                "naive_rag_tokens": naive_rag_tokens,
                "compression_rate": compression_rate,
                "avg_sdh_score": avg_sdh_score,
                "latency_ms": total_latency_ms,
                "model": effective_model,
                "inference_tokens": generated_tokens,
                "session_id": session_id,
                "answer_source": route.answer_source,
            },
        }
    )


async def _handle_ws_ingest(
    ws: WebSocket,
    data: dict[str, Any],
    user_sub: str = DEFAULT_USER,
) -> None:
    """Handle document ingestion with pipeline events over WebSocket."""
    text = data.get("text", "")
    if not isinstance(text, str):
        await ws.send_json({"type": "error", "detail": "Document text must be a string"})
        return
    doc_name = (str(data.get("document_name", "document")).strip() or "document")[:255]

    try:
        clean_text = sanitize_document(text)
        raw_layout = sanitize_document_layout(text)
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

    active_store = _store_for(user_sub)

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
            hardware=_get_hardware(),
            raw_document=raw_layout,
        )

    except Exception as exc:
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

    user_sub = DEFAULT_USER
    if auth_token:
        try:
            user_sub = validate_token(auth_token).get("sub") or DEFAULT_USER
            authenticated = True
        except HTTPException:
            authenticated = False

    await ws_manager.connect(ws)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except ValueError:
                data = None
            if not isinstance(data, dict):
                await ws.send_json(
                    {"type": "error", "detail": "Malformed message: expected a JSON object."}
                )
                continue
            msg_type = data.get("type")

            if msg_type == "ping":
                await ws.send_json({"type": "pong"})
                continue

            if msg_type == "auth":
                token_to_verify = data.get("token")
                if not isinstance(token_to_verify, str):
                    token_to_verify = ""
                try:
                    user_sub = validate_token(token_to_verify).get("sub") or DEFAULT_USER
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
                if isinstance(payload_token, str) and payload_token:
                    try:
                        user_sub = validate_token(payload_token).get("sub") or DEFAULT_USER
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

            if msg_type in ("query", "ingest"):
                handler = _handle_ws_query if msg_type == "query" else _handle_ws_ingest
                try:
                    await handler(ws, data, user_sub)
                except WebSocketDisconnect:
                    raise
                except Exception as exc:
                    print(f"WebSocket {msg_type} handler failed: {exc}")
                    await ws.send_json(
                        {"type": "error", "detail": f"{msg_type.capitalize()} failed"}
                    )

            else:
                await ws.send_json(
                    {
                        "type": "unknown_command",
                        "detail": f"Unrecognized type: {msg_type}",
                    }
                )

    except (WebSocketDisconnect, RuntimeError):
        # RuntimeError: the socket was already closed when we tried to send.
        pass
    finally:
        ws_manager.disconnect(ws)
