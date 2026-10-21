"""
Wires the full 6-stage offline pipeline:
    Stage 0: Hardware Detection and Calibration
    Stage 1: Neural Coreference Resolution
    Stage 2: SVOA Fact Extraction (Negation + Epistemic Modality + Adjuncts)
    Stage 3: Semantic Density Heuristic (SDH) Scoring & ChromaDB Ingestion
    Stage 4: Query-Adaptive Re-ranking, Modality Filtering & Context Packing
    Stage 5: Local LLM Inference (Ollama)

Provides clean entrypoints for document ingestion and question answering.
"""

import os
import re
import time
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any, Literal, overload

from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.coref import resolve_coreferences
from precis.pipeline.hardware import HardwareProfile, profile_hardware
from precis.pipeline.history import ChatMessage, session_manager
from precis.pipeline.inference import (
    OLLAMA_DEFAULT_BASE_URL,
    OllamaConnectionError,
    OllamaInferenceError,
    generate_answer,
    rewrite_followup_query,
)
from precis.pipeline.packer import pack_context, render_context
from precis.pipeline.routing import (
    QueryIntent,
    classify_query_intent,
    has_explicit_document_marker,
)
from precis.pipeline.sdh import score_facts_with_store
from precis.pipeline.structural import (
    assemble_structural_query_context,
    build_structural_context,
    extract_structural_evidence_from_document,
    is_list_extraction_enabled,
)
from precis.pipeline.svoa import extract_facts


@dataclass
class IngestionResult:
    """Telemetry and outcome from document ingestion."""

    document_name: str
    facts_extracted: int
    facts_stored: int
    latency_ms: int
    stage_timings: dict[str, int]
    facts: list[Fact] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Complete end-to-end outcome from question answering."""

    answer: str
    facts_used: list[Fact]
    tokens_used: int
    naive_rag_tokens: int
    compression_rate: float
    avg_sdh_score: float
    latency_ms: int
    stage_timings: dict[str, int]
    model: str = ""
    inference_tokens: int = 0
    # "conversation", "general" (model's own knowledge) or "document".
    answer_source: str = "document"


@dataclass
class ChatRoute:
    """Routing decision for one chat turn."""

    intent: QueryIntent
    answer_source: str  # "conversation" | "general" | "document"
    retrieval_query: str
    relevance: float | None = None


# Below this best query-fact cosine similarity a question is treated as
# unrelated to the documents. Measured on NQ pages (2026-10-21): questions
# about a page scored 0.29-0.78 against its facts, unrelated questions a
# median of 0.17. Kept low because routing a document question away from the
# documents costs more than the reverse: the document-chat prompt can still
# fall back to general knowledge.
CHAT_RELEVANCE_FLOOR = float(os.getenv("PRECIS_CHAT_RELEVANCE_FLOOR", "0.27"))

_FOLLOWUP_RE = re.compile(
    r"\b(it|its|they|them|their|this|that|these|those|he|him|his|she|her|there|then|same|former|latter|previous|earlier)\b"
    r"|^(what\s+about|how\s+about|and|also|so|but|why|how\s+come)\b",
    re.IGNORECASE,
)


def _looks_like_followup(query: str, history: list[ChatMessage]) -> bool:
    """A query that probably depends on earlier turns to be understood."""
    if not history:
        return False
    return bool(_FOLLOWUP_RE.search(query)) or len(query.split()) <= 4


def _standalone_query(
    query: str,
    history: list[ChatMessage],
    model: str,
    ollama_base_url: str,
) -> str:
    """Rewrite a follow-up as a standalone question for retrieval.

    Falls back to prefixing the previous user message when the model is
    unavailable, which is enough for embedding retrieval.
    """
    if not _looks_like_followup(query, history):
        return query
    try:
        return rewrite_followup_query(query, history, model=model, base_url=ollama_base_url)
    except (OllamaConnectionError, OllamaInferenceError):
        previous = next((t.content for t in reversed(history) if t.role == "user"), "")
        return f"{previous} {query}".strip()


def document_relevance(query: str, store: FactStore) -> float:
    """Best cosine similarity between the query and any stored fact or
    structural block (0.0 for an empty store)."""
    best = 0.0
    hits = store.query_similar(query, n_results=3)
    if hits:
        best = hits[0][1]
    if hasattr(store, "has_structural_evidence") and store.has_structural_evidence():
        blocks = store.query_similar_structural(query, n_results=3)
        if blocks:
            best = max(best, blocks[0][1])
    return best


def route_chat_query(
    query: str,
    store: FactStore,
    has_documents: bool,
    history: list[ChatMessage],
    model: str,
    ollama_base_url: str = OLLAMA_DEFAULT_BASE_URL,
) -> ChatRoute:
    """Decide how the chat app answers one turn.

    Casual messages and general questions go to the conversational prompt.
    Document questions are first made standalone (follow-ups), then sent to
    the documents unless nothing stored is related to them, in which case the
    model answers from its own knowledge.
    """
    intent = classify_query_intent(query, has_documents=has_documents, conversation_history=history)

    if intent == QueryIntent.CONVERSATIONAL:
        return ChatRoute(intent, "conversation", query)
    if intent == QueryIntent.GENERAL_KNOWLEDGE:
        return ChatRoute(intent, "general", query)
    if not has_documents:
        # Explicit document reference with nothing ingested; callers report it.
        return ChatRoute(intent, "document", query)

    retrieval_query = _standalone_query(query, history, model, ollama_base_url)
    # "What does the report say…" and an unresolved "explain this" with
    # documents loaded are about the documents whatever their similarity.
    if intent == QueryIntent.AMBIGUOUS or has_explicit_document_marker(query):
        return ChatRoute(QueryIntent.DOCUMENT_GROUNDED, "document", retrieval_query)

    relevance = document_relevance(retrieval_query, store)
    if relevance < CHAT_RELEVANCE_FLOOR:
        return ChatRoute(QueryIntent.GENERAL_KNOWLEDGE, "general", retrieval_query, relevance)
    return ChatRoute(QueryIntent.DOCUMENT_GROUNDED, "document", retrieval_query, relevance)


@dataclass
class AssembledQueryContext:
    """Telemetry and assembled prompt context for query execution."""

    context: str
    facts_used: list[Fact]
    tokens_used: int
    naive_rag_tokens: int
    compression_rate: float
    avg_sdh_score: float
    facts_packed: int
    use_structural: bool
    telemetry: dict[str, Any] = field(default_factory=dict)


def ingest_document(
    text: str,
    source_doc: str,
    store: FactStore,
    hardware: HardwareProfile | None = None,
    enable_list_extraction: bool | None = None,
    raw_document: str | None = None,
) -> IngestionResult:
    """
    Ingest document text through Stages 0 to 3 into the FactStore.

    Flow:
        Text -> Coreference Resolution (FCoref) ->
        SVOA Extraction (spaCy dependency tree) ->
        SDH Scoring (4 terms against existing store embeddings) ->
        ChromaDB Persistence
    """
    if not text or not text.strip():
        return IngestionResult(
            document_name=source_doc,
            facts_extracted=0,
            facts_stored=0,
            latency_ms=0,
            stage_timings={},
            facts=[],
        )

    timings: dict[str, int] = {}
    total_start = time.perf_counter()

    # Stage 0: Hardware profile
    t0 = time.perf_counter()

    if hardware is None:
        hardware = profile_hardware()

    timings["hardware_profile"] = int((time.perf_counter() - t0) * 1000)

    # Stage 0.5: Feature-flagged structural extraction and persistence
    list_enabled = is_list_extraction_enabled(enable_list_extraction)
    text_for_svoa = text
    pending_structural: list = []

    if list_enabled:
        doc_to_inspect = raw_document if raw_document and raw_document.strip() else text
        clean_prose, structural_records = extract_structural_evidence_from_document(
            raw_doc=doc_to_inspect,
            source_doc=source_doc,
        )
        # Persisted together with the facts at the end, so a failure in the
        # stages below cannot leave structural evidence without facts.
        pending_structural = structural_records
        if clean_prose and clean_prose.strip():
            text_for_svoa = clean_prose

    # Stage 1: Coreference resolution
    t0 = time.perf_counter()
    resolved_text = resolve_coreferences(text_for_svoa)

    timings["coreference"] = int((time.perf_counter() - t0) * 1000)

    # Stage 2: SVOA extraction
    t0 = time.perf_counter()
    facts = extract_facts(
        resolved_text,
        source_doc=source_doc,
    )

    timings["svoa_extraction"] = int((time.perf_counter() - t0) * 1000)

    # Stage 3: SDH scoring and store insertion
    t0 = time.perf_counter()
    # Re-ingesting a document replaces its previous facts and evidence. Done after
    # extraction so a failure in the earlier stages leaves the old version intact.
    # The old rows are kept aside so a failure while storing the new version can
    # put them back; scoring still sees the store without them, as before.
    previous = (
        store.snapshot_document(source_doc) if hasattr(store, "snapshot_document") else None
    )
    if hasattr(store, "delete_document"):
        store.delete_document(source_doc)

    try:
        scored_facts = score_facts_with_store(
            facts,
            store,
        )
        stored_count = store.add_facts(scored_facts)
        if pending_structural and hasattr(store, "add_structural_evidence"):
            store.add_structural_evidence(pending_structural)
    except Exception:
        # Do not leave a partially written document behind; restore the previous
        # version, if there was one, then report the original error.
        if hasattr(store, "delete_document"):
            store.delete_document(source_doc)
        if previous is not None:
            try:
                store.restore_document(previous)
            except Exception as restore_exc:
                print(f"Could not restore the previous version of {source_doc}: {restore_exc}")
        raise

    timings["sdh_scoring_and_storage"] = int((time.perf_counter() - t0) * 1000)

    total_elapsed = int((time.perf_counter() - total_start) * 1000)

    return IngestionResult(
        document_name=source_doc,
        facts_extracted=len(facts),
        facts_stored=stored_count,
        latency_ms=total_elapsed,
        stage_timings=timings,
        facts=scored_facts,
    )


run_ingest_document = ingest_document


def assemble_query_context(
    query: str,
    store: FactStore,
    token_ceiling: int,
    top_k: int = 100,
    exclude_modalities: set[str] | None = None,
    enable_list_extraction: bool | None = None,
    raw_document: str | None = None,
) -> AssembledQueryContext:
    """
    Unified query context builder shared by REST API, WebSocket handler, and query_pipeline.
    """
    list_enabled = is_list_extraction_enabled(enable_list_extraction)

    pack_res = pack_context(
        query=query,
        store=store,
        token_ceiling=token_ceiling,
        top_k=top_k,
        exclude_modalities=exclude_modalities,
    )

    if list_enabled:
        # Path A: explicit raw_document provided programmatically
        if raw_document and raw_document.strip():
            s_ctx, s_telem = build_structural_context(
                raw_doc=raw_document,
                query=query,
                token_ceiling=token_ceiling,
                enable_list_extraction=True,
            )
            if s_telem.get("content_list_blocks_found", 0) > 0:
                return AssembledQueryContext(
                    context=s_ctx,
                    facts_used=pack_res.packed_facts,
                    tokens_used=s_telem.get("total_context_estimated_tokens", pack_res.tokens_used),
                    naive_rag_tokens=pack_res.naive_rag_tokens or s_telem.get("clean_prose_estimated_tokens", 0),
                    compression_rate=pack_res.compression_rate,
                    avg_sdh_score=pack_res.avg_sdh_score,
                    facts_packed=pack_res.facts_packed,
                    use_structural=True,
                    telemetry=s_telem,
                )

        # Path B: persisted structural evidence in store
        if hasattr(store, "has_structural_evidence") and store.has_structural_evidence():
            s_ctx, s_facts, s_telem, is_struct = assemble_structural_query_context(
                query=query,
                store=store,
                token_ceiling=token_ceiling,
                top_k=top_k,
                exclude_modalities=exclude_modalities,
            )
            if is_struct:
                return AssembledQueryContext(
                    context=s_ctx,
                    facts_used=s_facts,
                    tokens_used=s_telem.get("total_context_estimated_tokens", pack_res.tokens_used),
                    naive_rag_tokens=pack_res.naive_rag_tokens,
                    compression_rate=pack_res.compression_rate,
                    avg_sdh_score=pack_res.avg_sdh_score,
                    facts_packed=len(s_facts),
                    use_structural=True,
                    telemetry=s_telem,
                )

    # Disabled mode or fallback to standard SVOA fact packing
    return AssembledQueryContext(
        context=render_context(pack_res.packed_facts),
        facts_used=pack_res.packed_facts,
        tokens_used=pack_res.tokens_used,
        naive_rag_tokens=pack_res.naive_rag_tokens,
        compression_rate=pack_res.compression_rate,
        avg_sdh_score=pack_res.avg_sdh_score,
        facts_packed=pack_res.facts_packed,
        use_structural=False,
    )


@overload
def query_pipeline(
    query: str,
    store: FactStore,
    hardware: HardwareProfile | None = None,
    model: str | None = None,
    top_k: int = 100,
    exclude_modalities: set[str] | None = None,
    stream: Literal[False] = False,
    ollama_base_url: str = OLLAMA_DEFAULT_BASE_URL,
    prompt_style: Literal["standard", "concise"] | None = None,
    raw_document: str | None = None,
    enable_list_extraction: bool | None = None,
    session_id: str | None = None,
    chat: bool = False,
) -> PipelineResult: ...


@overload
def query_pipeline(
    query: str,
    store: FactStore,
    hardware: HardwareProfile | None = None,
    model: str | None = None,
    top_k: int = 100,
    exclude_modalities: set[str] | None = None,
    stream: Literal[True] = True,
    ollama_base_url: str = OLLAMA_DEFAULT_BASE_URL,
    prompt_style: Literal["standard", "concise"] | None = None,
    raw_document: str | None = None,
    enable_list_extraction: bool | None = None,
    session_id: str | None = None,
    chat: bool = False,
) -> Generator[str, None, PipelineResult]: ...


def query_pipeline(
    query: str,
    store: FactStore,
    hardware: HardwareProfile | None = None,
    model: str | None = None,
    top_k: int = 100,
    exclude_modalities: set[str] | None = None,
    stream: bool = False,
    ollama_base_url: str = OLLAMA_DEFAULT_BASE_URL,
    prompt_style: Literal["standard", "concise"] | None = None,
    raw_document: str | None = None,
    enable_list_extraction: bool | None = None,
    session_id: str | None = None,
    chat: bool = False,
) -> PipelineResult | Generator[str, None, PipelineResult]:
    """
    Execute a query through Stages 0, 4, and 5 (or conversational path).

    Flow:
        Query -> Intent Classification & Session History ->
        If Conversational:
            Local LLM Conversational Generation (skipping vector retrieval)
        If Document-Grounded:
            ChromaDB Similarity Retrieval ->
            Modality Filtering & Re-ranking ->
            Token Budget Packing ->
            Context Rendering ->
            Ollama Local LLM Response Generation.

    When stream=False, returns a PipelineResult directly.
    When stream=True, returns a generator that yields response tokens
    and returns a PipelineResult when exhausted.

    chat=True is the chat app's behaviour (route_chat_query): follow-ups are
    rewritten for retrieval, questions unrelated to the documents are answered
    from general knowledge, and document answers use the document_chat prompt
    with the conversation history. chat=False keeps the evaluated grounded
    prompt.
    """
    timings: dict[str, int] = {}
    total_start = time.perf_counter()

    # Stage 0: Hardware profile calibration
    t0 = time.perf_counter()

    if hardware is None:
        hardware = profile_hardware()

    timings["hardware_profile"] = int((time.perf_counter() - t0) * 1000)

    selected_model = model or hardware.recommended_model

    has_svoa = store.count() > 0 if store is not None else False
    has_struct = (
        is_list_extraction_enabled(enable_list_extraction)
        and hasattr(store, "has_structural_evidence")
        and store.has_structural_evidence()
    ) if store is not None else False
    has_docs = has_svoa or has_struct or bool(raw_document and raw_document.strip())

    history = session_manager.get_history(session_id) if session_id else []
    if chat:
        route = route_chat_query(
            query, store, has_docs, history, selected_model, ollama_base_url
        )
    else:
        intent = classify_query_intent(query, has_documents=has_docs, conversation_history=history)
        route = ChatRoute(
            intent,
            {
                QueryIntent.CONVERSATIONAL: "conversation",
                QueryIntent.GENERAL_KNOWLEDGE: "general",
            }.get(intent, "document"),
            query,
        )
    intent = route.intent
    answer_source = route.answer_source

    # Conversational Path
    if answer_source != "document":
        if stream:
            def stream_conversational() -> Generator[str, None, PipelineResult]:
                inference_start = time.perf_counter()
                inference_generator = generate_answer(
                    query=query,
                    context="",
                    model=selected_model,
                    stream=True,
                    base_url=ollama_base_url,
                    prompt_style=prompt_style,
                    prompt_type="conversational",
                    history=history,
                )

                while True:
                    try:
                        token = next(inference_generator)
                        yield token
                    except StopIteration as exc:
                        inference_result = exc.value
                        break

                timings["inference"] = int((time.perf_counter() - inference_start) * 1000)
                total_ms = int((time.perf_counter() - total_start) * 1000)

                if session_id:
                    session_manager.add_message(session_id, "user", query)
                    session_manager.add_message(session_id, "assistant", inference_result.answer)

                return PipelineResult(
                    answer=inference_result.answer,
                    facts_used=[],
                    tokens_used=0,
                    naive_rag_tokens=0,
                    compression_rate=0.0,
                    avg_sdh_score=0.0,
                    latency_ms=total_ms,
                    stage_timings=timings,
                    model=selected_model,
                    inference_tokens=inference_result.tokens_generated,
                    answer_source=answer_source,
                )

            return stream_conversational()

        t0_inf = time.perf_counter()
        inference_result = generate_answer(
            query=query,
            context="",
            model=selected_model,
            stream=False,
            base_url=ollama_base_url,
            prompt_style=prompt_style,
            prompt_type="conversational",
            history=history,
        )
        timings["inference"] = int((time.perf_counter() - t0_inf) * 1000)
        total_ms = int((time.perf_counter() - total_start) * 1000)

        if session_id:
            session_manager.add_message(session_id, "user", query)
            session_manager.add_message(session_id, "assistant", inference_result.answer)

        return PipelineResult(
            answer=inference_result.answer,
            facts_used=[],
            tokens_used=0,
            naive_rag_tokens=0,
            compression_rate=0.0,
            avg_sdh_score=0.0,
            latency_ms=total_ms,
            stage_timings=timings,
            model=selected_model,
            inference_tokens=inference_result.tokens_generated,
            answer_source=answer_source,
        )

    # Document-Grounded Path
    if intent == QueryIntent.AMBIGUOUS and not has_docs:
        # Ambiguous without docs -> clarify
        clarification = "Could you please clarify your question or specify what you are referring to?"
        total_ms = int((time.perf_counter() - total_start) * 1000)
        if session_id:
            session_manager.add_message(session_id, "user", query)
            session_manager.add_message(session_id, "assistant", clarification)
        return PipelineResult(
            answer=clarification,
            facts_used=[],
            tokens_used=0,
            naive_rag_tokens=0,
            compression_rate=0.0,
            avg_sdh_score=0.0,
            latency_ms=total_ms,
            stage_timings=timings,
            model=selected_model,
            inference_tokens=len(clarification.split()),
        )

    # Stage 4: Re-ranking and context packing
    t0 = time.perf_counter()

    assembled = assemble_query_context(
        query=route.retrieval_query,
        store=store,
        token_ceiling=hardware.token_ceiling,
        top_k=top_k,
        exclude_modalities=exclude_modalities,
        enable_list_extraction=enable_list_extraction,
        raw_document=raw_document,
    )

    context = assembled.context
    facts_used = assembled.facts_used
    tokens_used = assembled.tokens_used
    naive_rag_tokens = assembled.naive_rag_tokens
    compression_rate = assembled.compression_rate
    avg_sdh_score = assembled.avg_sdh_score

    timings["rerank_and_pack"] = int((time.perf_counter() - t0) * 1000)

    # Stage 5: Local LLM inference
    if stream:

        def stream_pipeline() -> Generator[str, None, PipelineResult]:
            inference_start = time.perf_counter()

            inference_generator = generate_answer(
                query=query,
                context=context,
                model=selected_model,
                stream=True,
                base_url=ollama_base_url,
                prompt_style=prompt_style,
                prompt_type="document_chat" if chat else "grounded",
                history=history if chat else None,
            )

            while True:
                try:
                    token = next(inference_generator)
                    yield token
                except StopIteration as exc:
                    inference_result = exc.value
                    break

            timings["inference"] = int((time.perf_counter() - inference_start) * 1000)

            total_ms = int((time.perf_counter() - total_start) * 1000)

            if session_id:
                session_manager.add_message(session_id, "user", query)
                session_manager.add_message(session_id, "assistant", inference_result.answer, grounded=True)

            return PipelineResult(
                answer=inference_result.answer,
                facts_used=facts_used,
                tokens_used=tokens_used,
                naive_rag_tokens=naive_rag_tokens,
                compression_rate=compression_rate,
                avg_sdh_score=avg_sdh_score,
                latency_ms=total_ms,
                stage_timings=timings,
                model=selected_model,
                inference_tokens=inference_result.tokens_generated,
                answer_source=answer_source,
            )

        return stream_pipeline()

    t0_inf = time.perf_counter()
    inference_result = generate_answer(
        query=query,
        context=context,
        model=selected_model,
        stream=False,
        base_url=ollama_base_url,
        prompt_style=prompt_style,
        prompt_type="document_chat" if chat else "grounded",
        history=history if chat else None,
    )

    timings["inference"] = int((time.perf_counter() - t0_inf) * 1000)

    total_ms = int((time.perf_counter() - total_start) * 1000)

    if session_id:
        session_manager.add_message(session_id, "user", query)
        session_manager.add_message(session_id, "assistant", inference_result.answer, grounded=True)

    return PipelineResult(
        answer=inference_result.answer,
        facts_used=facts_used,
        tokens_used=tokens_used,
        naive_rag_tokens=naive_rag_tokens,
        compression_rate=compression_rate,
        avg_sdh_score=avg_sdh_score,
        latency_ms=total_ms,
        stage_timings=timings,
        model=selected_model,
        inference_tokens=inference_result.tokens_generated,
        answer_source=answer_source,
    )


def process_query(
    document_text: str,
    query: str,
    store: FactStore,
    hardware: HardwareProfile | None = None,
    source_doc: str = "document",
    model: str | None = None,
    ollama_base_url: str = OLLAMA_DEFAULT_BASE_URL,
    enable_list_extraction: bool | None = None,
) -> PipelineResult:
    """
    Convenience helper.

    Ingests document text when provided, then executes a non-streaming
    query against the resulting FactStore.
    """
    if document_text and document_text.strip():
        ingest_document(
            document_text,
            source_doc,
            store,
            hardware=hardware,
            enable_list_extraction=enable_list_extraction,
            raw_document=document_text,
        )


    return query_pipeline(
        query=query,
        store=store,
        hardware=hardware,
        model=model,
        stream=False,
        ollama_base_url=ollama_base_url,
        raw_document=document_text,
        enable_list_extraction=enable_list_extraction,
    )
