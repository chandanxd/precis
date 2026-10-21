"""
Runs research benchmarks against NaturalQuestions dataset samples:

- Baseline A: Naive RAG (512-word chunking, top-k retrieval)
- Baseline B: Précis without modality filtering
- Full Précis: 6-stage SVOA pipeline with SDH scoring and epistemic filtering
- SDH Ablation: Drop E(s,o), I(v), U(t,G), A(t) individually

Computes:
- Exact Match
- ROUGE-L
- BERTScore
- Context token consumption
- Generated token consumption
- Compression rate
- Query latency

Formats publication-ready markdown tables for paper assembly.

Notes:
- Document ingestion is performed once per sample and is excluded from
  query latency because the benchmark measures QA after indexing.
- Ablation conditions reuse the same resolved/extracted facts and vary
  only the SDH weighting configuration.
- Missing datasets fail loudly unless --synthetic is explicitly supplied.
"""

from __future__ import annotations

import argparse
import datetime
import gc
import json
import os
import random
import time
from collections.abc import Sequence
from dataclasses import dataclass

from typing import Any

from precis.evaluation.metrics import (
    DEFAULT_BERTSCORE_MODEL,
    compute_bert_score,
    compute_exact_match,
    compute_minilm_cosine,
    compute_rouge_l,
    is_bertscore_model_cached,
)
from precis.evaluation.naive_rag import naive_rag_answer
from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.coref import resolve_coreferences
from precis.pipeline.inference import (
    InferenceResult,
    OLLAMA_DEFAULT_BASE_URL,
    generate_answer,
)
from precis.pipeline.orchestrator import ingest_document
from precis.pipeline.packer import (
    PackResult,
    _estimate_naive_rag_tokens,
    estimate_fact_tokens,
    pack_context,
    render_context,
)
from precis.pipeline.sdh import (
    ABLATION_DROP_ALPHA,
    ABLATION_DROP_BETA,
    ABLATION_DROP_DELTA,
    ABLATION_DROP_GAMMA,
    DEFAULT_WEIGHTS,
    score_facts,
)
from precis.pipeline.svoa import extract_facts

DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_TOKEN_CEILING = 2048
DEFAULT_LIMIT = 200
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 512
DEFAULT_SEED = 42


@dataclass
class DatasetStats:
    """Summary statistics from dataset ingestion and validation."""

    path: str
    requested_limit: int
    total_lines: int
    valid_count: int
    skipped_count: int
    duplicate_count: int
    skip_reasons: dict[str, int]
    sample_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "requested_limit": self.requested_limit,
            "total_lines": self.total_lines,
            "valid_count": self.valid_count,
            "skipped_count": self.skipped_count,
            "duplicate_count": self.duplicate_count,
            "skip_reasons": self.skip_reasons,
            "sample_ids": self.sample_ids,
        }


@dataclass
class EvalSample:
    """A single QA evaluation instance."""

    question: str
    gold_answer: str
    document: str
    doc_id: str = "doc_0"


@dataclass
class EvalResult:
    """Individual sample evaluation outcome."""

    question: str
    gold_answer: str
    predicted_answer: str
    exact_match: bool
    rouge_l: float
    bert_score: float | None

    # Context/prompt-side measurements.
    context_words: int

    # Model output-side measurement.
    generated_tokens: int

    # Fraction of the naive context budget removed by Précis.
    compression_rate: float

    # Query-time latency only. Document ingestion is intentionally excluded.
    latency_ms: int

    # MiniLM sentence embedding cosine similarity (distinct from BERTScore).
    minilm_cosine: float | None = None

    # Granular sample tracking and statistical analysis fields:
    sample_id: str = ""
    condition: str = ""
    facts_considered: int = 0
    facts_packed: int = 0
    avg_sdh_score: float = 0.0
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    top_p: float = DEFAULT_TOP_P
    max_tokens: int = DEFAULT_MAX_TOKENS
    context_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "condition": self.condition,
            "question": self.question,
            "gold_answer": self.gold_answer,
            "predicted_answer": self.predicted_answer,
            "exact_match": self.exact_match,
            "rouge_l": self.rouge_l,
            "bert_score": self.bert_score,
            "minilm_cosine": self.minilm_cosine,
            "context_words": self.context_words,
            "context_tokens": self.context_tokens,
            "generated_tokens": self.generated_tokens,
            "compression_rate": self.compression_rate,
            "latency_ms": self.latency_ms,
            "facts_considered": self.facts_considered,
            "facts_packed": self.facts_packed,
            "avg_sdh_score": self.avg_sdh_score,
            "model": self.model,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }


@dataclass
class AggregateResult:
    """Aggregated benchmark statistics across multiple samples."""

    condition: str
    num_samples: int

    avg_em: float
    avg_rouge_l: float
    avg_bert_score: float | None

    avg_context_words: int
    avg_generated_tokens: int

    avg_compression_rate: float
    avg_latency_ms: int

    avg_minilm_cosine: float | None = None
    avg_facts_considered: float = 0.0
    avg_facts_packed: float = 0.0
    avg_sdh_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "num_samples": self.num_samples,
            "avg_em": self.avg_em,
            "avg_rouge_l": self.avg_rouge_l,
            "avg_bert_score": self.avg_bert_score,
            "avg_minilm_cosine": self.avg_minilm_cosine,
            "avg_context_words": self.avg_context_words,
            "avg_generated_tokens": self.avg_generated_tokens,
            "avg_compression_rate": self.avg_compression_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "avg_facts_considered": self.avg_facts_considered,
            "avg_facts_packed": self.avg_facts_packed,
            "avg_sdh_score": self.avg_sdh_score,
        }


ABLATION_CONFIGS: dict[str, dict[str, float]] = {
    "full": DEFAULT_WEIGHTS,
    "drop_E": ABLATION_DROP_ALPHA,
    "drop_I": ABLATION_DROP_BETA,
    "drop_U": ABLATION_DROP_GAMMA,
    "drop_A": ABLATION_DROP_DELTA,
}


def _validate_sample(sample: EvalSample, index: int) -> None:
    """Validate the minimum fields required for benchmark execution."""

    if not sample.question.strip():
        raise ValueError(f"Sample {index} has an empty question.")

    if not sample.gold_answer.strip():
        raise ValueError(f"Sample {index} has an empty gold answer.")

    if not sample.document.strip():
        raise ValueError(f"Sample {index} has an empty document.")

    if not sample.doc_id.strip():
        raise ValueError(f"Sample {index} has an empty document ID.")


def _make_collection_name(
    prefix: str,
    sample_index: int,
    config: str = "",
) -> str:
    """Create a deterministic, Chroma-safe collection name."""

    suffix = f"_{config}" if config else ""

    return (f"precis_eval_{prefix}_{sample_index}{suffix}")[:63]


def load_natural_questions(
    path: str,
    limit: int = DEFAULT_LIMIT,
    skip_invalid: bool = False,
    return_stats: bool = False,
) -> list[EvalSample] | tuple[list[EvalSample], DatasetStats]:
    """
    Load evaluation samples from a JSONL file.

    `limit` applies to valid evaluation samples rather than raw JSONL lines.
    Empty lines are ignored.
    """
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Evaluation dataset not found: {path}")

    samples: list[EvalSample] = []
    seen_questions: set[str] = set()
    skip_reasons: dict[str, int] = {}
    sample_ids: list[str] = []
    total_lines = 0
    duplicate_count = 0

    with open(path, "r", encoding="utf-8") as f:
        line_number = 0

        for raw_line in f:
            line_number += 1
            line = raw_line.strip()

            if not line:
                continue

            total_lines += 1

            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                if skip_invalid:
                    skip_reasons["json_decode_error"] = (
                        skip_reasons.get("json_decode_error", 0) + 1
                    )
                    continue
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}: {exc}"
                ) from exc

            if not isinstance(data, dict):
                if skip_invalid:
                    skip_reasons["non_object"] = (
                        skip_reasons.get("non_object", 0) + 1
                    )
                    continue
                raise TypeError(
                    f"Expected an object on line {line_number} of {path}."
                )

            question = data.get("question", "")
            gold_answer = data.get(
                "answer",
                data.get("gold_answer", ""),
            )
            document = data.get(
                "document",
                data.get("context", ""),
            )
            doc_id = data.get(
                "doc_id",
                f"doc_{len(samples)}",
            )

            if not isinstance(question, str):
                if skip_invalid:
                    skip_reasons["non_string_question"] = (
                        skip_reasons.get("non_string_question", 0) + 1
                    )
                    continue
                raise TypeError(
                    f"Sample on line {line_number} has a non-string question."
                )

            if not isinstance(gold_answer, str):
                if skip_invalid:
                    skip_reasons["non_string_gold_answer"] = (
                        skip_reasons.get("non_string_gold_answer", 0) + 1
                    )
                    continue
                raise TypeError(
                    f"Sample on line {line_number} has non-string gold answer."
                )

            if not isinstance(document, str):
                if skip_invalid:
                    skip_reasons["non_string_document"] = (
                        skip_reasons.get("non_string_document", 0) + 1
                    )
                    continue
                raise TypeError(
                    f"Sample on line {line_number} has a non-string document."
                )

            if not isinstance(doc_id, str):
                if skip_invalid:
                    skip_reasons["non_string_doc_id"] = (
                        skip_reasons.get("non_string_doc_id", 0) + 1
                    )
                    continue
                raise TypeError(
                    f"Sample on line {line_number} has a non-string doc_id."
                )

            sample = EvalSample(
                question=question,
                gold_answer=gold_answer,
                document=document,
                doc_id=doc_id,
            )

            try:
                _validate_sample(sample, line_number)
            except ValueError:
                if skip_invalid:
                    reason = "empty_field"
                    if not question.strip():
                        reason = "empty_question"
                    elif not gold_answer.strip():
                        reason = "empty_gold_answer"
                    elif not document.strip():
                        reason = "empty_document"
                    elif not doc_id.strip():
                        reason = "empty_doc_id"
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    continue
                raise

            norm_q = question.strip().lower()
            if norm_q in seen_questions:
                duplicate_count += 1
                if skip_invalid:
                    skip_reasons["duplicate_question"] = (
                        skip_reasons.get("duplicate_question", 0) + 1
                    )
                    continue
            seen_questions.add(norm_q)

            samples.append(sample)
            sample_ids.append(sample.doc_id)

            if len(samples) >= limit:
                break

    stats = DatasetStats(
        path=path,
        requested_limit=limit,
        total_lines=total_lines,
        valid_count=len(samples),
        skipped_count=sum(skip_reasons.values()),
        duplicate_count=duplicate_count,
        skip_reasons=skip_reasons,
        sample_ids=sample_ids,
    )

    if return_stats:
        return samples, stats
    return samples


def aggregate_results(
    condition: str,
    results: Sequence[EvalResult],
) -> AggregateResult:
    """Compute mean averages across sample results."""
    n = len(results)

    if n == 0:
        return AggregateResult(
            condition=condition,
            num_samples=0,
            avg_em=0.0,
            avg_rouge_l=0.0,
            avg_bert_score=None,
            avg_context_words=0,
            avg_generated_tokens=0,
            avg_compression_rate=0.0,
            avg_latency_ms=0,
            avg_minilm_cosine=None,
            avg_facts_considered=0.0,
            avg_facts_packed=0.0,
            avg_sdh_score=0.0,
        )

    valid_bert = [r.bert_score for r in results if r.bert_score is not None]
    avg_bert = (
        round(sum(valid_bert) / len(valid_bert), 4) if valid_bert else None
    )

    valid_minilm = [
        r.minilm_cosine for r in results if r.minilm_cosine is not None
    ]
    avg_minilm = (
        round(sum(valid_minilm) / len(valid_minilm), 4)
        if valid_minilm
        else None
    )

    return AggregateResult(
        condition=condition,
        num_samples=n,
        avg_em=round(
            sum(1.0 for r in results if r.exact_match) / n,
            4,
        ),
        avg_rouge_l=round(
            sum(r.rouge_l for r in results) / n,
            4,
        ),
        avg_bert_score=avg_bert,
        avg_context_words=int(sum(r.context_words for r in results) / n),
        avg_generated_tokens=int(sum(r.generated_tokens for r in results) / n),
        avg_compression_rate=round(
            sum(r.compression_rate for r in results) / n,
            4,
        ),
        avg_latency_ms=int(sum(r.latency_ms for r in results) / n),
        avg_minilm_cosine=avg_minilm,
        avg_facts_considered=round(
            sum(r.facts_considered for r in results) / n, 2
        ),
        avg_facts_packed=round(
            sum(r.facts_packed for r in results) / n, 2
        ),
        avg_sdh_score=round(
            sum(r.avg_sdh_score for r in results) / n, 4
        ),
    )


def _evaluate_answer(
    question: str,
    gold_answer: str,
    predicted_answer: str,
    context_words: int,
    generated_tokens: int,
    compression_rate: float,
    latency_ms: int,
    use_bertscore: bool = False,
    bertscore_model: str = DEFAULT_BERTSCORE_MODEL,
    device: str | None = None,
    sample_id: str = "",
    condition: str = "",
    facts_considered: int = 0,
    facts_packed: int = 0,
    avg_sdh_score: float = 0.0,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    context_tokens: int = 0,
) -> EvalResult:
    """Construct a standardized evaluation result."""
    exact_match = compute_exact_match(
        predicted_answer,
        gold_answer,
    )
    rouge_l = compute_rouge_l(
        predicted_answer,
        gold_answer,
    )
    minilm_cosine = compute_minilm_cosine(
        predicted_answer,
        gold_answer,
    )

    bert_score: float | None = None
    if use_bertscore:
        bert_score = compute_bert_score(
            predicted_answer,
            gold_answer,
            model_type=bertscore_model,
            device=device,
        )

    return EvalResult(
        question=question,
        gold_answer=gold_answer,
        predicted_answer=predicted_answer,
        exact_match=exact_match,
        rouge_l=rouge_l,
        bert_score=bert_score,
        context_words=context_words,
        generated_tokens=generated_tokens,
        compression_rate=compression_rate,
        latency_ms=latency_ms,
        minilm_cosine=minilm_cosine,
        sample_id=sample_id,
        condition=condition,
        facts_considered=facts_considered,
        facts_packed=facts_packed,
        avg_sdh_score=avg_sdh_score,
        model=model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        context_tokens=context_tokens,
    )


def pack_svoa_similarity(
    query: str,
    store: FactStore,
    token_ceiling: int,
    top_k: int = 100,
) -> PackResult:
    """
    Execute SVOA similarity baseline packing.

    Retrieves candidates using identical ChromaDB query as `pack_context`,
    disables modality filtering, and ranks facts by query similarity:
        ranking_score = query_similarity
    omitting the Semantic Density Heuristic (SDH) weighting entirely.
    """
    if (
        not query
        or not query.strip()
        or store.count() == 0
        or token_ceiling <= 0
        or top_k <= 0
    ):
        return PackResult([], 0, 0, 0.0, 0.0, 0, 0)

    # 1. Retrieve candidates from ChromaDB using vector similarity query.
    candidates = store.query_similar(query, n_results=top_k)
    if not candidates:
        return PackResult([], 0, 0, 0.0, 0.0, 0, 0)

    all_retrieved_facts = [fact for fact, _ in candidates]
    naive_tokens = _estimate_naive_rag_tokens(all_retrieved_facts)

    # 2. No modality filtering: all candidate facts are retained.
    filtered_pairs = candidates

    # 3. Pure query-similarity ranking (ranking_score = query_similarity).
    scored_candidates = [
        (fact, round(max(0.0, min(1.0, float(sim))), 4))
        for fact, sim in filtered_pairs
    ]
    scored_candidates.sort(key=lambda item: item[1], reverse=True)

    # 4. Greedily pack facts into token ceiling using token estimation.
    packed: list[Fact] = []
    tokens_used = 0

    for fact, _ in scored_candidates:
        fact_tokens = estimate_fact_tokens(fact)
        if tokens_used + fact_tokens <= token_ceiling:
            packed.append(fact)
            tokens_used += fact_tokens

    compression_rate = (
        1.0 - (tokens_used / naive_tokens) if naive_tokens > 0 else 0.0
    )
    avg_sdh = (
        sum(fact.sdh_score for fact in packed) / len(packed)
        if packed
        else 0.0
    )

    return PackResult(
        packed_facts=packed,
        tokens_used=tokens_used,
        naive_rag_tokens=naive_tokens,
        compression_rate=round(max(0.0, compression_rate), 4),
        avg_sdh_score=round(avg_sdh, 4),
        facts_considered=len(filtered_pairs),
        facts_packed=len(packed),
    )


def run_evaluation(
    samples: list[EvalSample],
    model: str = DEFAULT_MODEL,
    token_ceiling: int = DEFAULT_TOKEN_CEILING,
    base_url: str = OLLAMA_DEFAULT_BASE_URL,
    use_bertscore: bool | None = None,
    bertscore_model: str = DEFAULT_BERTSCORE_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    return_individual: bool = False,
    mock_inference: bool = False,
) -> dict[str, AggregateResult] | tuple[
    dict[str, AggregateResult], dict[str, list[EvalResult]]
]:
    """
    Execute the main evaluation across research conditions:

    1. naive_rag: Baseline A (512-word chunking, top-k retrieval)
    2. svoa_similarity: Baseline B (SVOA propositions ranked by query
       similarity only)
    3. svoa_no_modality: Baseline C (SVOA ranked by SDH * similarity,
       no modality filter)
    4. precis_full: Full Précis 6-stage pipeline (SVOA + SDH +
       modality-filtered packing)

    Note: precis_no_modality is retained as an alias for svoa_no_modality.
    """
    if token_ceiling <= 0:
        raise ValueError("token_ceiling must be greater than zero.")

    if use_bertscore is None:
        use_bertscore = (
            os.environ.get("PRECIS_USE_BERTSCORE") == "1"
            or os.environ.get("PRECIS_USE_DEBERTA_BERTSCORE") == "1"
        )

    conditions: dict[str, list[EvalResult]] = {
        "naive_rag": [],
        "svoa_similarity": [],
        "svoa_no_modality": [],
        "precis_no_modality": [],
        "precis_full": [],
    }

    for i, sample in enumerate(samples):
        _validate_sample(sample, i)

        print(f"[{i + 1}/{len(samples)}] Evaluating: {sample.question[:80]}")

        # ------------------------------------------------------------------
        # 1. Baseline A: Naive RAG
        # ------------------------------------------------------------------

        t0 = time.perf_counter()

        naive_answer, naive_context_words, naive_tokens_generated = naive_rag_answer(
            document=sample.document,
            query=sample.question,
            model_name=model,
            base_url=base_url,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            mock_inference=mock_inference,
        )

        naive_latency = int((time.perf_counter() - t0) * 1000)

        conditions["naive_rag"].append(
            _evaluate_answer(
                question=sample.question,
                gold_answer=sample.gold_answer,
                predicted_answer=naive_answer,
                context_words=naive_context_words,
                generated_tokens=naive_tokens_generated,
                compression_rate=0.0,
                latency_ms=naive_latency,
                use_bertscore=use_bertscore,
                bertscore_model=bertscore_model,
                sample_id=sample.doc_id,
                condition="naive_rag",
                facts_considered=0,
                facts_packed=0,
                avg_sdh_score=0.0,
                model=model,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                context_tokens=int(naive_context_words * 1.3),
            )
        )

        # ------------------------------------------------------------------
        # 2, 3, 4. Précis & SVOA Conditions
        # Ingest once, then run all fact conditions against the same store.
        # ------------------------------------------------------------------

        store = FactStore(
            in_memory=True,
            collection_name=_make_collection_name(
                "main",
                i,
            ),
        )

        try:
            ingest_document(
                sample.document,
                sample.doc_id,
                store,
            )

            # --------------------------------------------------------------
            # Baseline B: SVOA Pure Similarity (No SDH, No Modality Filter)
            # --------------------------------------------------------------

            t0 = time.perf_counter()

            pack_sim = pack_svoa_similarity(
                query=sample.question,
                store=store,
                token_ceiling=token_ceiling,
            )

            ctx_sim = render_context(pack_sim.packed_facts)
            context_words_sim = len(ctx_sim.split())

            if mock_inference:
                ans_text = ctx_sim[:100].strip() if ctx_sim else "No context."
                inf_sim = InferenceResult(
                    answer=ans_text,
                    model=model,
                    latency_ms=10,
                    tokens_generated=len(ans_text.split()),
                )
            else:
                inf_sim = generate_answer(
                    sample.question,
                    ctx_sim,
                    model=model,
                    base_url=base_url,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )

            lat_sim = int((time.perf_counter() - t0) * 1000)

            conditions["svoa_similarity"].append(
                _evaluate_answer(
                    question=sample.question,
                    gold_answer=sample.gold_answer,
                    predicted_answer=inf_sim.answer,
                    context_words=context_words_sim,
                    generated_tokens=inf_sim.tokens_generated,
                    compression_rate=pack_sim.compression_rate,
                    latency_ms=lat_sim,
                    use_bertscore=use_bertscore,
                    bertscore_model=bertscore_model,
                    sample_id=sample.doc_id,
                    condition="svoa_similarity",
                    facts_considered=pack_sim.facts_considered,
                    facts_packed=pack_sim.facts_packed,
                    avg_sdh_score=pack_sim.avg_sdh_score,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    context_tokens=pack_sim.tokens_used,
                )
            )

            # --------------------------------------------------------------
            # Baseline C: SVOA w/o Modality Filtering (SDH + Similarity)
            # --------------------------------------------------------------

            t0 = time.perf_counter()

            pack_b = pack_context(
                query=sample.question,
                store=store,
                token_ceiling=token_ceiling,
                exclude_modalities=set(),
            )

            ctx_b = render_context(pack_b.packed_facts)
            context_words_b = len(ctx_b.split())

            if mock_inference:
                ans_text = ctx_b[:100].strip() if ctx_b else "No context."
                inf_b = InferenceResult(
                    answer=ans_text,
                    model=model,
                    latency_ms=10,
                    tokens_generated=len(ans_text.split()),
                )
            else:
                inf_b = generate_answer(
                    sample.question,
                    ctx_b,
                    model=model,
                    base_url=base_url,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )

            lat_b = int((time.perf_counter() - t0) * 1000)

            no_mod_eval = _evaluate_answer(
                question=sample.question,
                gold_answer=sample.gold_answer,
                predicted_answer=inf_b.answer,
                context_words=context_words_b,
                generated_tokens=inf_b.tokens_generated,
                compression_rate=pack_b.compression_rate,
                latency_ms=lat_b,
                use_bertscore=use_bertscore,
                bertscore_model=bertscore_model,
                sample_id=sample.doc_id,
                condition="svoa_no_modality",
                facts_considered=pack_b.facts_considered,
                facts_packed=pack_b.facts_packed,
                avg_sdh_score=pack_b.avg_sdh_score,
                model=model,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                context_tokens=pack_b.tokens_used,
            )
            conditions["svoa_no_modality"].append(no_mod_eval)
            conditions["precis_no_modality"].append(no_mod_eval)

            # --------------------------------------------------------------
            # Full Précis: 6-Stage (SDH + Similarity, Modality Filtered)
            # --------------------------------------------------------------

            t0 = time.perf_counter()

            pack_full = pack_context(
                query=sample.question,
                store=store,
                token_ceiling=token_ceiling,
            )

            ctx_full = render_context(pack_full.packed_facts)
            context_words_full = len(ctx_full.split())

            if mock_inference:
                ans_text = (
                    ctx_full[:100].strip() if ctx_full else "No context."
                )
                inf_full = InferenceResult(
                    answer=ans_text,
                    model=model,
                    latency_ms=10,
                    tokens_generated=len(ans_text.split()),
                )
            else:
                inf_full = generate_answer(
                    sample.question,
                    ctx_full,
                    model=model,
                    base_url=base_url,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )

            lat_full = int((time.perf_counter() - t0) * 1000)

            conditions["precis_full"].append(
                _evaluate_answer(
                    question=sample.question,
                    gold_answer=sample.gold_answer,
                    predicted_answer=inf_full.answer,
                    context_words=context_words_full,
                    generated_tokens=inf_full.tokens_generated,
                    compression_rate=pack_full.compression_rate,
                    latency_ms=lat_full,
                    use_bertscore=use_bertscore,
                    bertscore_model=bertscore_model,
                    sample_id=sample.doc_id,
                    condition="precis_full",
                    facts_considered=pack_full.facts_considered,
                    facts_packed=pack_full.facts_packed,
                    avg_sdh_score=pack_full.avg_sdh_score,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    context_tokens=pack_full.tokens_used,
                )
            )

        finally:
            try:
                store.clear()
                store._client.delete_collection(name=store.collection_name)
            except Exception:
                pass
            gc.collect()

    agg = {
        key: aggregate_results(key, values)
        for key, values in conditions.items()
    }
    if return_individual:
        return agg, conditions
    return agg


def run_ablation(
    samples: list[EvalSample],
    model: str = DEFAULT_MODEL,
    token_ceiling: int = DEFAULT_TOKEN_CEILING,
    base_url: str = OLLAMA_DEFAULT_BASE_URL,
    use_bertscore: bool | None = None,
    bertscore_model: str = DEFAULT_BERTSCORE_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    return_individual: bool = False,
    mock_inference: bool = False,
) -> dict[str, AggregateResult] | tuple[
    dict[str, AggregateResult], dict[str, list[EvalResult]]
]:
    """
    Execute the SDH ablation study.

    Each condition uses the same:
    - source document
    - coreference resolution
    - SVOA extraction
    - query
    - token ceiling
    - model

    Only the SDH weighting configuration changes.
    """

    if token_ceiling <= 0:
        raise ValueError("token_ceiling must be greater than zero.")

    if use_bertscore is None:
        use_bertscore = (
            os.environ.get("PRECIS_USE_BERTSCORE") == "1"
            or os.environ.get("PRECIS_USE_DEBERTA_BERTSCORE") == "1"
        )

    ablation_results: dict[str, list[EvalResult]] = {
        key: [] for key in ABLATION_CONFIGS
    }

    for i, sample in enumerate(samples):
        _validate_sample(sample, i)

        print(f"[Ablation {i + 1}/{len(samples)}] {sample.question[:80]}")

        # Resolve and extract exactly once per sample.
        resolved = resolve_coreferences(sample.document)

        raw_facts = extract_facts(
            resolved,
            source_doc=sample.doc_id,
        )

        for config_name, weights in ABLATION_CONFIGS.items():
            store = FactStore(
                in_memory=True,
                collection_name=_make_collection_name(
                    "ablation",
                    i,
                    config_name,
                ),
            )

            try:
                # Score the identical extracted facts with the selected
                # SDH weighting configuration.
                scored = score_facts(
                    list(raw_facts),
                    weights=weights,
                )

                store.add_facts(scored)

                t0 = time.perf_counter()

                pack = pack_context(
                    query=sample.question,
                    store=store,
                    token_ceiling=token_ceiling,
                )

                ctx = render_context(pack.packed_facts)

                if mock_inference:
                    ans_text = ctx[:100].strip() if ctx else "No context."
                    inf = InferenceResult(
                        answer=ans_text,
                        model=model,
                        latency_ms=10,
                        tokens_generated=len(ans_text.split()),
                    )
                else:
                    inf = generate_answer(
                        sample.question,
                        ctx,
                        model=model,
                        base_url=base_url,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                    )

                lat = int((time.perf_counter() - t0) * 1000)
                context_words = len(ctx.split())

                ablation_results[config_name].append(
                    _evaluate_answer(
                        question=sample.question,
                        gold_answer=sample.gold_answer,
                        predicted_answer=inf.answer,
                        context_words=context_words,
                        generated_tokens=inf.tokens_generated,
                        compression_rate=pack.compression_rate,
                        latency_ms=lat,
                        use_bertscore=use_bertscore,
                        bertscore_model=bertscore_model,
                        sample_id=sample.doc_id,
                        condition=f"ablation_{config_name}",
                        facts_considered=pack.facts_considered,
                        facts_packed=pack.facts_packed,
                        avg_sdh_score=pack.avg_sdh_score,
                        model=model,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                        context_tokens=pack.tokens_used,
                    )
                )

            finally:
                try:
                    store.clear()
                    store._client.delete_collection(name=store.collection_name)
                except Exception:
                    pass
                gc.collect()

    agg = {
        key: aggregate_results(key, values)
        for key, values in ablation_results.items()
    }
    if return_individual:
        return agg, ablation_results
    return agg


def format_results_table(
    results: dict[str, AggregateResult],
    title: str = "Main Evaluation Results",
) -> str:
    """Format evaluation comparison table as GitHub markdown."""

    has_bert = any(r.avg_bert_score is not None for r in results.values())
    has_minilm = any(r.avg_minilm_cosine is not None for r in results.values())

    headers = ["Condition", "EM", "ROUGE-L"]
    if has_bert:
        headers.append("BERTScore (DeBERTa)")
    if has_minilm:
        headers.append("MiniLM Cosine")
    headers.extend([
        "Context Words",
        "Generated Tokens",
        "Compression Rate",
        "Latency",
    ])

    lines = [
        f"### {title}\n",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]

    names = {
        "naive_rag": "Baseline A (Naive RAG 512-chunk)",
        "svoa_similarity": "Baseline B (SVOA Pure Similarity)",
        "svoa_no_modality": "Baseline C (SVOA w/o Modality)",
        "precis_no_modality": "Baseline C (SVOA w/o Modality)",
        "precis_full": "**Précis (Full 6-Stage)**",
    }

    for key, result in results.items():
        if key == "precis_no_modality" and "svoa_no_modality" in results:
            continue
        display_name = names.get(
            key,
            key,
        )

        row = [
            display_name,
            f"{result.avg_em:.3f}",
            f"{result.avg_rouge_l:.3f}",
        ]
        if has_bert:
            row.append(
                f"{result.avg_bert_score:.3f}"
                if result.avg_bert_score is not None
                else "-"
            )
        if has_minilm:
            row.append(
                f"{result.avg_minilm_cosine:.3f}"
                if result.avg_minilm_cosine is not None
                else "-"
            )
        row.extend([
            f"{result.avg_context_words}",
            f"{result.avg_generated_tokens}",
            f"{result.avg_compression_rate:.1%}",
            f"{result.avg_latency_ms}ms",
        ])
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def format_ablation_table(
    results: dict[str, AggregateResult],
    title: str = "SDH Ablation Study",
) -> str:
    """Format SDH ablation table as GitHub markdown."""

    has_bert = any(r.avg_bert_score is not None for r in results.values())
    has_minilm = any(r.avg_minilm_cosine is not None for r in results.values())

    headers = ["Configuration", "Dropped Term", "EM", "ROUGE-L"]
    if has_bert:
        headers.append("BERTScore (DeBERTa)")
    if has_minilm:
        headers.append("MiniLM Cosine")
    headers.extend([
        "Δ ROUGE-L",
        "Context Words",
        "Compression Rate",
    ])

    lines = [
        f"### {title}\n",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]

    descriptions = {
        "full": (
            "None (Full SDH)",
            "-",
        ),
        "drop_E": (
            "Entity Relatedness E(s,o)",
            "α = 0",
        ),
        "drop_I": (
            "Verb Informativeness I(v)",
            "β = 0",
        ),
        "drop_U": (
            "Uniqueness U(t,G)",
            "γ = 0",
        ),
        "drop_A": (
            "Adjunct Density A(t)",
            "δ = 0",
        ),
    }

    full_result = results.get("full")
    base_rouge = full_result.avg_rouge_l if full_result else 0.0

    for key, result in results.items():
        term_desc, dropped = descriptions.get(
            key,
            (key, ""),
        )

        delta = result.avg_rouge_l - base_rouge

        delta_str = f"{delta:+.3f}" if key != "full" else "-"

        bold_prefix = "**" if key == "full" else ""

        bold_suffix = "**" if key == "full" else ""

        row = [
            f"{bold_prefix}{key}{bold_suffix}",
            f"{term_desc} ({dropped})",
            f"{result.avg_em:.3f}",
            f"{result.avg_rouge_l:.3f}",
        ]
        if has_bert:
            row.append(
                f"{result.avg_bert_score:.3f}"
                if result.avg_bert_score is not None
                else "-"
            )
        if has_minilm:
            row.append(
                f"{result.avg_minilm_cosine:.3f}"
                if result.avg_minilm_cosine is not None
                else "-"
            )
        row.extend([
            delta_str,
            f"{result.avg_context_words}",
            f"{result.avg_compression_rate:.1%}",
        ])
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def build_smoke_test_samples(count: int = 5) -> list[EvalSample]:
    """Return deterministic smoke-test evaluation samples."""

    samples = [
        EvalSample(
            question="Who discovered penicillin in 1928?",
            gold_answer="Dr. Alexander Fleming",
            document=(
                "In 1928, Dr. Alexander Fleming discovered penicillin "
                "at St. Mary's Hospital in London. "
                "He observed that a mould contaminated a "
                "Staphylococcus culture and inhibited its growth. "
                "The medicine became widely used during World War II."
            ),
            doc_id="smoke_penicillin",
        ),
        EvalSample(
            question="Who was the first person to walk on the Moon?",
            gold_answer="Neil Armstrong",
            document=(
                "On July 20, 1969, American astronaut Neil Armstrong "
                "became the first person to walk on the Moon. "
                "He stepped off the Apollo 11 Lunar Module Eagle onto "
                "the lunar surface. "
                "Armstrong declared the event as one small step for man, "
                "one giant leap for mankind."
            ),
            doc_id="smoke_apollo11",
        ),
        EvalSample(
            question=(
                "Who introduced the concept of the universal Turing machine "
                "in 1936?"
            ),
            gold_answer="Alan Turing",
            document=(
                "In 1936, British mathematician Alan Turing published "
                "On Computable Numbers, introducing the concept of the "
                "universal Turing machine. "
                "His theoretical model formed the foundational framework "
                "of modern computer science. "
                "Turing later contributed significantly to cryptanalysis "
                "during the war."
            ),
            doc_id="smoke_turing",
        ),
        EvalSample(
            question="What organelle conducts photosynthesis in plant cells?",
            gold_answer="chloroplasts",
            document=(
                "Plant cells conduct photosynthesis primarily inside "
                "specialized organelles called chloroplasts. "
                "Chloroplasts contain the green pigment chlorophyll "
                "which absorbs sunlight. "
                "This biochemical process converts light energy into "
                "chemical energy, synthesizing glucose from carbon "
                "dioxide and water while releasing oxygen."
            ),
            doc_id="smoke_photosynthesis",
        ),
        EvalSample(
            question=(
                "Who discovered the double helix structure of DNA in 1953?"
            ),
            gold_answer="James Watson and Francis Crick",
            document=(
                "In 1953, James Watson and Francis Crick proposed "
                "the double helix model of DNA. "
                "They conducted their research at the Cavendish Laboratory "
                "at the University of Cambridge. "
                "Their molecular model explained how genetic information "
                "is stored and replicated in living organisms."
            ),
            doc_id="smoke_dna",
        ),
    ]
    return samples[:count]


def build_synthetic_sample() -> EvalSample:
    """Return the explicit development-only synthetic benchmark sample."""

    return EvalSample(
        question="Who discovered penicillin in 1928?",
        gold_answer="Dr. Alexander Fleming",
        document=(
            "In 1928, Dr. Alexander Fleming discovered penicillin "
            "at St. Mary's Hospital in London. "
            "He observed that a mould contaminated a "
            "Staphylococcus culture and inhibited its growth. "
            "The medicine became widely used during World War II."
        ),
        doc_id="sample_penicillin",
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description=("Précis Evaluation and Benchmarking Suite")
    )

    parser.add_argument(
        "--data",
        default="data/nq_subset/nq_dev.jsonl",
        help="Path to evaluation JSONL.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum number of valid samples to evaluate.",
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Ollama model identifier.",
    )

    parser.add_argument(
        "--token-ceiling",
        type=int,
        default=DEFAULT_TOKEN_CEILING,
        help="Précis context token budget ceiling.",
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=(
            "Inference temperature (default 0.0 for deterministic greedy "
            "decoding)."
        ),
    )

    parser.add_argument(
        "--top-p",
        type=float,
        default=DEFAULT_TOP_P,
        help="Inference nucleus sampling top_p (default 0.9).",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="Maximum generated tokens per answer (default 512).",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Random seed for reproducible evaluation runs (default 42).",
    )

    parser.add_argument(
        "--output-dir",
        default="paper/tables",
        help="Directory to export markdown tables and telemetry JSON.",
    )

    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help=(
            "Run 5 deterministic smoke-test samples across all experimental "
            "conditions."
        ),
    )

    parser.add_argument(
        "--synthetic",
        action="store_true",
        help=(
            "Run the built-in single synthetic development sample "
            "instead of loading the dataset."
        ),
    )

    parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help="Skip invalid dataset records instead of raising ValueError.",
    )

    parser.add_argument(
        "--mock-inference",
        action="store_true",
        help=(
            "Use deterministic mock inference instead of calling live "
            "Ollama LLM."
        ),
    )

    parser.add_argument(
        "--skip-ablation",
        action="store_true",
        help="Run only the main benchmark.",
    )

    parser.add_argument(
        "--bertscore",
        action="store_true",
        help="Compute genuine BERTScore using DeBERTa contextual embeddings.",
    )

    parser.add_argument(
        "--bertscore-model",
        default=DEFAULT_BERTSCORE_MODEL,
        help="Pretrained model identifier for BERTScore.",
    )

    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for running benchmarks."""

    args = parse_args()

    if args.limit <= 0:
        raise SystemExit("--limit must be greater than zero.")

    if args.token_ceiling <= 0:
        raise SystemExit("--token-ceiling must be greater than zero.")

    random.seed(args.seed)

    use_bertscore = args.bertscore or (
        os.environ.get("PRECIS_USE_BERTSCORE") == "1"
        or os.environ.get("PRECIS_USE_DEBERTA_BERTSCORE") == "1"
    )

    if use_bertscore:
        is_offline = (
            os.environ.get("HF_HUB_OFFLINE") == "1"
            or os.environ.get("TRANSFORMERS_OFFLINE") == "1"
        )
        if is_offline and not is_bertscore_model_cached(args.bertscore_model):
            raise SystemExit(
                f"BERTScore model '{args.bertscore_model}' is not cached "
                "locally. Cannot download in offline mode. Pre-cache model."
            )

    dataset_stats: dict[str, Any] | None = None

    if args.smoke_test:
        samples = build_smoke_test_samples(count=min(args.limit, 5))
        print(
            f"Using {len(samples)} deterministic smoke-test evaluation "
            "samples."
        )
    elif args.synthetic:
        samples = [build_synthetic_sample()]
        print("Using synthetic development benchmark sample.")
    else:
        if not os.path.exists(args.data):
            raise SystemExit(
                f"Dataset file not found at: '{args.data}'.\n"
                "Expected input: A JSONL file containing Natural Questions "
                "evaluation samples.\n"
                "Required schema per line (JSON):\n"
                "  - 'question': str (the benchmark query)\n"
                "  - 'answer' or 'gold_answer': str (the reference answer)\n"
                "  - 'document' or 'context': str (source document/passage)\n"
                "  - 'doc_id' (optional): str (unique document identifier)\n\n"
                "To obtain the dataset, download the Natural Questions dev "
                "split (v1.0-simplified or MRQA 2019 NQ dev split)\n"
                "and convert/extract samples into JSONL format at "
                "'data/nq_subset/nq_dev.jsonl'.\n"
                "To validate the harness without the external dataset, use "
                "--smoke-test or --synthetic."
            )

        print(
            f"Loading evaluation samples from {args.data} "
            f"(limit={args.limit})..."
        )

        try:
            samples, stats = load_natural_questions(
                args.data,
                limit=args.limit,
                skip_invalid=args.skip_invalid,
                return_stats=True,
            )
            dataset_stats = stats.to_dict()
            print(
                f"Dataset stats: total_lines={stats.total_lines}, "
                f"valid={stats.valid_count}, skipped={stats.skipped_count}, "
                f"duplicates={stats.duplicate_count}"
            )
        except (
            OSError,
            ValueError,
            TypeError,
        ) as exc:
            raise SystemExit(
                f"Failed to load evaluation dataset: {exc}"
            ) from exc

    if not samples:
        raise SystemExit("The evaluation dataset contained no valid samples.")

    print(f"Loaded {len(samples)} evaluation samples.")

    print(
        "\nRunning Main Benchmarks (Naive RAG vs SVOA Similarity vs Précis)..."
    )

    main_results, individual_main = run_evaluation(
        samples,
        model=args.model,
        token_ceiling=args.token_ceiling,
        use_bertscore=use_bertscore,
        bertscore_model=args.bertscore_model,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        return_individual=True,
        mock_inference=args.mock_inference,
    )

    main_table = format_results_table(main_results)

    print("\n" + main_table)

    if args.output_dir:
        os.makedirs(
            args.output_dir,
            exist_ok=True,
        )

        main_output_path = os.path.join(
            args.output_dir,
            "main_results.md",
        )

        with open(
            main_output_path,
            "w",
            encoding="utf-8",
        ) as f:
            f.write(main_table)
            f.write("\n")

        # Export granular per-question results for paired statistical testing
        per_question_path = os.path.join(
            args.output_dir,
            "per_question_results.jsonl",
        )

        with open(
            per_question_path,
            "w",
            encoding="utf-8",
        ) as f:
            for cond_name, res_list in individual_main.items():
                if (
                    cond_name == "precis_no_modality"
                    and "svoa_no_modality" in individual_main
                ):
                    continue
                for res in res_list:
                    f.write(json.dumps(res.to_dict()) + "\n")

        # Export benchmark metadata
        metadata = {
            "timestamp": (
                datetime.datetime.now(datetime.timezone.utc).isoformat()
            ),
            "benchmark_config": {
                "dataset_path": (
                    args.data
                    if not (args.smoke_test or args.synthetic)
                    else None
                ),
                "dataset_mode": (
                    "smoke_test"
                    if args.smoke_test
                    else ("synthetic" if args.synthetic else "file")
                ),
                "limit": args.limit,
                "samples_evaluated": len(samples),
                "model": args.model,
                "temperature": args.temperature,
                "top_p": args.top_p,
                "max_tokens": args.max_tokens,
                "token_ceiling": args.token_ceiling,
                "seed": args.seed,
                "mock_inference": args.mock_inference,
                "use_bertscore": use_bertscore,
                "bertscore_model": (
                    args.bertscore_model if use_bertscore else None
                ),
            },
            "dataset_stats": dataset_stats,
            "aggregate_main_results": {
                k: v.to_dict() for k, v in main_results.items()
            },
            "aggregate_ablation_results": None,
        }
        metadata_path = os.path.join(
            args.output_dir,
            "benchmark_metadata.json",
        )
        with open(
            metadata_path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(metadata, f, indent=2)

        print(
            f"\nMain benchmark tables and telemetry successfully written to "
            f"{args.output_dir}/"
        )

    ablation_results: dict[str, AggregateResult] | None = None
    individual_ablation: dict[str, list[EvalResult]] | None = None
    ablation_table: str | None = None

    if not args.skip_ablation:
        print("\nRunning SDH Ablation Study...")

        ablation_results, individual_ablation = run_ablation(
            samples,
            model=args.model,
            token_ceiling=args.token_ceiling,
            use_bertscore=use_bertscore,
            bertscore_model=args.bertscore_model,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            return_individual=True,
            mock_inference=args.mock_inference,
        )

        ablation_table = format_ablation_table(ablation_results)

        print("\n" + ablation_table)

        if args.output_dir:
            if ablation_table is not None:
                ablation_output_path = os.path.join(
                    args.output_dir,
                    "ablation_results.md",
                )

                with open(
                    ablation_output_path,
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(ablation_table)
                    f.write("\n")

            if individual_ablation:
                with open(
                    per_question_path,
                    "a",
                    encoding="utf-8",
                ) as f:
                    for cond_name, res_list in individual_ablation.items():
                        for res in res_list:
                            f.write(json.dumps(res.to_dict()) + "\n")

            metadata["aggregate_ablation_results"] = {
                k: v.to_dict() for k, v in ablation_results.items()
            }
            with open(
                metadata_path,
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(metadata, f, indent=2)

            print(
                f"\nAblation tables and telemetry successfully written to "
                f"{args.output_dir}/"
            )


if __name__ == "__main__":
    main()
