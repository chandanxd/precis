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
import json
import os
import time
from collections.abc import Sequence
from dataclasses import dataclass

from precis.evaluation.metrics import (
    compute_bert_score,
    compute_exact_match,
    compute_rouge_l,
)
from precis.evaluation.naive_rag import naive_rag_answer
from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.coref import resolve_coreferences
from precis.pipeline.inference import (
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
DEFAULT_LIMIT = 20


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
    bert_score: float

    # Context/prompt-side measurements.
    context_words: int

    # Model output-side measurement.
    generated_tokens: int

    # Fraction of the naive context budget removed by Précis.
    compression_rate: float

    # Query-time latency only. Document ingestion is intentionally excluded.
    latency_ms: int


@dataclass
class AggregateResult:
    """Aggregated benchmark statistics across multiple samples."""

    condition: str
    num_samples: int

    avg_em: float
    avg_rouge_l: float
    avg_bert_score: float

    avg_context_words: int
    avg_generated_tokens: int

    avg_compression_rate: float
    avg_latency_ms: int


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


def _make_collection_name(prefix: str, sample_index: int, config: str = "") -> str:
    """Create a deterministic, Chroma-safe collection name."""

    suffix = f"_{config}" if config else ""

    return (f"precis_eval_{prefix}_{sample_index}{suffix}")[:63]


def load_natural_questions(
    path: str,
    limit: int = DEFAULT_LIMIT,
) -> list[EvalSample]:
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

    with open(path, "r", encoding="utf-8") as f:
        line_number = 0

        for raw_line in f:
            line_number += 1

            line = raw_line.strip()

            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}: {exc}"
                ) from exc

            if not isinstance(data, dict):
                raise TypeError(f"Expected an object on line {line_number} of {path}.")

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
                raise TypeError(
                    f"Sample on line {line_number} has a non-string question."
                )

            if not isinstance(gold_answer, str):
                raise TypeError(
                    f"Sample on line {line_number} has a non-string gold answer."
                )

            if not isinstance(document, str):
                raise TypeError(
                    f"Sample on line {line_number} has a non-string document."
                )

            if not isinstance(doc_id, str):
                raise TypeError(
                    f"Sample on line {line_number} has a non-string doc_id."
                )

            sample = EvalSample(
                question=question,
                gold_answer=gold_answer,
                document=document,
                doc_id=doc_id,
            )

            _validate_sample(sample, line_number)

            samples.append(sample)

            if len(samples) >= limit:
                break

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
            avg_bert_score=0.0,
            avg_context_words=0,
            avg_generated_tokens=0,
            avg_compression_rate=0.0,
            avg_latency_ms=0,
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
        avg_bert_score=round(
            sum(r.bert_score for r in results) / n,
            4,
        ),
        avg_context_words=int(sum(r.context_words for r in results) / n),
        avg_generated_tokens=int(sum(r.generated_tokens for r in results) / n),
        avg_compression_rate=round(
            sum(r.compression_rate for r in results) / n,
            4,
        ),
        avg_latency_ms=int(sum(r.latency_ms for r in results) / n),
    )


def _evaluate_answer(
    question: str,
    gold_answer: str,
    predicted_answer: str,
    context_words: int,
    generated_tokens: int,
    compression_rate: float,
    latency_ms: int,
) -> EvalResult:
    """Construct a standardized evaluation result."""

    return EvalResult(
        question=question,
        gold_answer=gold_answer,
        predicted_answer=predicted_answer,
        exact_match=compute_exact_match(
            predicted_answer,
            gold_answer,
        ),
        rouge_l=compute_rouge_l(
            predicted_answer,
            gold_answer,
        ),
        bert_score=compute_bert_score(
            predicted_answer,
            gold_answer,
        ),
        context_words=context_words,
        generated_tokens=generated_tokens,
        compression_rate=compression_rate,
        latency_ms=latency_ms,
    )


def pack_svoa_similarity(
    query: str,
    store: FactStore,
    token_ceiling: int,
    top_k: int = 100,
) -> PackResult:
    """
    Execute SVOA similarity baseline packing.

    Retrieves candidates using the identical ChromaDB query as `pack_context`,
    disables modality filtering, and ranks facts strictly by embedding query similarity:
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

    # 1. Retrieve candidates from ChromaDB using identical vector similarity query.
    candidates = store.query_similar(query, n_results=top_k)
    if not candidates:
        return PackResult([], 0, 0, 0.0, 0.0, 0, 0)

    all_retrieved_facts = [fact for fact, _ in candidates]
    naive_tokens = _estimate_naive_rag_tokens(all_retrieved_facts)

    # 2. No modality filtering: all candidate facts are retained.
    filtered_pairs = candidates

    # 3. Pure query-similarity ranking (ranking_score = query_similarity; no SDH weighting).
    scored_candidates = [
        (fact, round(max(0.0, min(1.0, float(sim))), 4)) for fact, sim in filtered_pairs
    ]
    scored_candidates.sort(key=lambda item: item[1], reverse=True)

    # 4. Greedily pack facts into the token ceiling using standard token estimation.
    packed: list[Fact] = []
    tokens_used = 0

    for fact, _ in scored_candidates:
        fact_tokens = estimate_fact_tokens(fact)
        if tokens_used + fact_tokens <= token_ceiling:
            packed.append(fact)
            tokens_used += fact_tokens

    compression_rate = 1.0 - (tokens_used / naive_tokens) if naive_tokens > 0 else 0.0
    avg_sdh = sum(fact.sdh_score for fact in packed) / len(packed) if packed else 0.0

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
) -> dict[str, AggregateResult]:
    """
    Execute the main evaluation across research conditions:

    1. naive_rag: Baseline A (512-word chunking, top-k retrieval)
    2. svoa_similarity: Baseline B (SVOA propositions ranked by query similarity only)
    3. svoa_no_modality: Baseline C (SVOA ranked by SDH * similarity, no modality filter)
    4. precis_full: Full Précis 6-stage pipeline (SVOA + SDH + modality-filtered packing)

    Note: precis_no_modality is retained as an alias for svoa_no_modality.
    """
    if token_ceiling <= 0:
        raise ValueError("token_ceiling must be greater than zero.")

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

        naive_answer, naive_context_words = naive_rag_answer(
            document=sample.document,
            query=sample.question,
            model_name=model,
            base_url=base_url,
        )

        naive_latency = int((time.perf_counter() - t0) * 1000)

        conditions["naive_rag"].append(
            _evaluate_answer(
                question=sample.question,
                gold_answer=sample.gold_answer,
                predicted_answer=naive_answer,
                context_words=naive_context_words,
                generated_tokens=0,
                compression_rate=0.0,
                latency_ms=naive_latency,
            )
        )

        # ------------------------------------------------------------------
        # 2, 3, 4. Précis & SVOA Conditions
        # Ingest once, then run all fact conditions against the identical store.
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

            inf_sim = generate_answer(
                sample.question,
                ctx_sim,
                model=model,
                base_url=base_url,
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

            inf_b = generate_answer(
                sample.question,
                ctx_b,
                model=model,
                base_url=base_url,
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

            inf_full = generate_answer(
                sample.question,
                ctx_full,
                model=model,
                base_url=base_url,
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
                )
            )

        finally:
            # FactStore is in-memory, so clearing the collection is sufficient.
            store.clear()

    return {key: aggregate_results(key, values) for key, values in conditions.items()}


def run_ablation(
    samples: list[EvalSample],
    model: str = DEFAULT_MODEL,
    token_ceiling: int = DEFAULT_TOKEN_CEILING,
    base_url: str = OLLAMA_DEFAULT_BASE_URL,
) -> dict[str, AggregateResult]:
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

                inf = generate_answer(
                    sample.question,
                    ctx,
                    model=model,
                    base_url=base_url,
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
                    )
                )

            finally:
                store.clear()

    return {
        key: aggregate_results(key, values) for key, values in ablation_results.items()
    }


def format_results_table(
    results: dict[str, AggregateResult],
    title: str = "Main Evaluation Results",
) -> str:
    """Format evaluation comparison table as GitHub markdown."""

    lines = [
        f"### {title}\n",
        (
            "| Condition | EM | ROUGE-L | BERTScore | "
            "Context Words | Generated Tokens | "
            "Compression Rate | Latency |"
        ),
        "|---|---|---|---|---|---|---|---|",
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

        lines.append(
            f"| {display_name} | "
            f"{result.avg_em:.3f} | "
            f"{result.avg_rouge_l:.3f} | "
            f"{result.avg_bert_score:.3f} | "
            f"{result.avg_context_words} | "
            f"{result.avg_generated_tokens} | "
            f"{result.avg_compression_rate:.1%} | "
            f"{result.avg_latency_ms}ms |"
        )

    return "\n".join(lines)


def format_ablation_table(
    results: dict[str, AggregateResult],
    title: str = "SDH Ablation Study",
) -> str:
    """Format SDH ablation table as GitHub markdown."""

    lines = [
        f"### {title}\n",
        (
            "| Configuration | Dropped Term | EM | ROUGE-L | "
            "BERTScore | Δ ROUGE-L | Context Words | "
            "Compression Rate |"
        ),
        "|---|---|---|---|---|---|---|---|",
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

        lines.append(
            f"| {bold_prefix}{key}{bold_suffix} | "
            f"{term_desc} ({dropped}) | "
            f"{result.avg_em:.3f} | "
            f"{result.avg_rouge_l:.3f} | "
            f"{result.avg_bert_score:.3f} | "
            f"{delta_str} | "
            f"{result.avg_context_words} | "
            f"{result.avg_compression_rate:.1%} |"
        )

    return "\n".join(lines)


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
        "--output-dir",
        default="paper/tables",
        help="Directory to export markdown tables.",
    )

    parser.add_argument(
        "--synthetic",
        action="store_true",
        help=(
            "Run the built-in synthetic development sample "
            "instead of loading the dataset."
        ),
    )

    parser.add_argument(
        "--skip-ablation",
        action="store_true",
        help="Run only the main benchmark.",
    )

    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for running benchmarks."""

    args = parse_args()

    if args.limit <= 0:
        raise SystemExit("--limit must be greater than zero.")

    if args.token_ceiling <= 0:
        raise SystemExit("--token-ceiling must be greater than zero.")

    if args.synthetic:
        samples = [build_synthetic_sample()]

        print("Using synthetic development benchmark sample.")
    else:
        print(f"Loading evaluation samples from {args.data} (limit={args.limit})...")

        try:
            samples = load_natural_questions(
                args.data,
                limit=args.limit,
            )
        except (
            OSError,
            ValueError,
            TypeError,
        ) as exc:
            raise SystemExit(f"Failed to load evaluation dataset: {exc}") from exc

    if not samples:
        raise SystemExit("The evaluation dataset contained no valid samples.")

    print(f"Loaded {len(samples)} evaluation samples.")

    print("\nRunning Main Benchmarks (Naive RAG vs Précis)...")

    main_results = run_evaluation(
        samples,
        model=args.model,
        token_ceiling=args.token_ceiling,
    )

    main_table = format_results_table(main_results)

    print("\n" + main_table)

    ablation_table: str | None = None

    if not args.skip_ablation:
        print("\nRunning SDH Ablation Study...")

        ablation_results = run_ablation(
            samples,
            model=args.model,
            token_ceiling=args.token_ceiling,
        )

        ablation_table = format_ablation_table(ablation_results)

        print("\n" + ablation_table)

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

        print(f"\nTables successfully written to {args.output_dir}/")


if __name__ == "__main__":
    main()
