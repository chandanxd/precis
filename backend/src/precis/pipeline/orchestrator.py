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

import time
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Literal, overload

from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.coref import resolve_coreferences
from precis.pipeline.hardware import HardwareProfile, profile_hardware
from precis.pipeline.inference import (
    OLLAMA_DEFAULT_BASE_URL,
    generate_answer,
)
from precis.pipeline.packer import pack_context, render_context
from precis.pipeline.sdh import score_facts_with_store
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


def ingest_document(
    text: str,
    source_doc: str,
    store: FactStore,
    hardware: HardwareProfile | None = None,
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

    # Stage 1: Coreference resolution
    t0 = time.perf_counter()
    resolved_text = resolve_coreferences(text)

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
    scored_facts = score_facts_with_store(
        facts,
        store,
    )
    stored_count = store.add_facts(scored_facts)

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
) -> PipelineResult | Generator[str, None, PipelineResult]:
    """
    Execute a query through Stages 0, 4, and 5.

    Flow:
        Query -> Hardware Calibration ->
        ChromaDB Similarity Retrieval ->
        Modality Filtering & Re-ranking ->
        Token Budget Packing ->
        Context Rendering ->
        Ollama Local LLM Response Generation.

    When stream=False, returns a PipelineResult directly.

    When stream=True, returns a generator that yields response tokens
    and returns a PipelineResult when exhausted.
    """
    timings: dict[str, int] = {}
    total_start = time.perf_counter()

    # Stage 0: Hardware profile calibration
    t0 = time.perf_counter()

    if hardware is None:
        hardware = profile_hardware()

    timings["hardware_profile"] = int((time.perf_counter() - t0) * 1000)

    selected_model = model or hardware.recommended_model

    # Stage 4: Re-ranking and context packing
    t0 = time.perf_counter()

    pack_res = pack_context(
        query=query,
        store=store,
        token_ceiling=hardware.token_ceiling,
        top_k=top_k,
        exclude_modalities=exclude_modalities,
    )

    context = render_context(pack_res.packed_facts)

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

            return PipelineResult(
                answer=inference_result.answer,
                facts_used=pack_res.packed_facts,
                tokens_used=pack_res.tokens_used,
                naive_rag_tokens=pack_res.naive_rag_tokens,
                compression_rate=pack_res.compression_rate,
                avg_sdh_score=pack_res.avg_sdh_score,
                latency_ms=total_ms,
                stage_timings=timings,
                model=selected_model,
                inference_tokens=inference_result.tokens_generated,
            )

        return stream_pipeline()

    inference_result = generate_answer(
        query=query,
        context=context,
        model=selected_model,
        stream=False,
        base_url=ollama_base_url,
    )

    timings["inference"] = int((time.perf_counter() - t0) * 1000)

    total_ms = int((time.perf_counter() - total_start) * 1000)

    return PipelineResult(
        answer=inference_result.answer,
        facts_used=pack_res.packed_facts,
        tokens_used=pack_res.tokens_used,
        naive_rag_tokens=pack_res.naive_rag_tokens,
        compression_rate=pack_res.compression_rate,
        avg_sdh_score=pack_res.avg_sdh_score,
        latency_ms=total_ms,
        stage_timings=timings,
        model=selected_model,
        inference_tokens=inference_result.tokens_generated,
    )


def process_query(
    document_text: str,
    query: str,
    store: FactStore,
    hardware: HardwareProfile | None = None,
    source_doc: str = "document",
    model: str | None = None,
    ollama_base_url: str = OLLAMA_DEFAULT_BASE_URL,
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
        )

    return query_pipeline(
        query=query,
        store=store,
        hardware=hardware,
        model=model,
        stream=False,
        ollama_base_url=ollama_base_url,
    )
