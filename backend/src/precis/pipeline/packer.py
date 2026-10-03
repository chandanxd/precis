"""
Combines intrinsic fact quality (SDH score) with query relevance:
    pack_score(t, q) = SDH(t) × cosine_sim(embed(t), embed(q))

Enforces epistemic modality filtering (asserted > attributed > conditional;
hypothetical excluded by default) and greedily packs top-scoring facts into
a hardware-adaptive token ceiling, outputting structured context and
compression metrics.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from precis.graph.schema import Fact
from precis.graph.store import FactStore

# Modality priority tiering: higher number = prioritized under score ties.
MODALITY_PRIORITY: dict[str, int] = {
    "asserted": 4,
    "attributed": 3,
    "conditional": 2,
    "hypothetical": 1,
}

# By default, hypothetical assertions are pruned from retrieval context.
DEFAULT_EXCLUDED_MODALITIES: set[str] = {"hypothetical"}


@dataclass
class PackResult:
    """Telemetry and context result from query-adaptive packing."""

    packed_facts: list[Fact]
    tokens_used: int
    naive_rag_tokens: int
    compression_rate: float
    avg_sdh_score: float
    facts_considered: int
    facts_packed: int


def _get_excluded_modalities(
    exclude_modalities: set[str] | None,
) -> set[str]:
    """Return the modality set to exclude from retrieval context."""
    if exclude_modalities is None:
        return DEFAULT_EXCLUDED_MODALITIES
    return exclude_modalities


def _render_fact_parts(fact: Fact) -> list[str]:
    """
    Build the textual components used to render a fact.

    Keeps token estimation and actual context rendering based on the same
    representation so the estimated budget better matches the final output.
    """
    if fact.negated:
        core = f"{fact.subject} NOT {fact.verb} {fact.object}"
    else:
        core = f"{fact.subject} {fact.verb} {fact.object}"

    parts: list[str] = [core]

    if isinstance(fact.adjuncts, dict):
        for key in sorted(fact.adjuncts):
            values = fact.adjuncts[key]

            if isinstance(values, list):
                for value in values:
                    if value and str(value).strip():
                        parts.append(f"({key}: {str(value).strip()})")
            elif isinstance(values, str) and values.strip():
                parts.append(f"({key}: {values.strip()})")

    if fact.modality == "attributed" and fact.attributed_to:
        parts.append(f"[attributed to {fact.attributed_to.strip()}]")
    elif fact.modality == "conditional":
        parts.append("[conditional]")
    elif fact.modality == "hypothetical":
        parts.append("[hypothetical]")

    return parts


def estimate_fact_tokens(fact: Fact) -> int:
    """
    Estimate subword token count for a fact when rendered in prompt context.

    Uses a subword expansion ratio (~1.3x words) plus structural overhead
    for the "Fact N:" label.
    """
    rendered_text = " ".join(_render_fact_parts(fact))
    words = len(rendered_text.split())

    # Approximate subword tokenization plus "Fact N:" structural overhead.
    return max(3, int(words * 1.3) + 2)


def compute_pack_score(
    fact: Fact,
    query_similarity: float,
) -> float:
    """
    Compute query-adaptive packing score:

        pack_score(t, q) = SDH(t) × cosine_sim(embed(t), embed(q))

    Both factors are bounded in [0.0, 1.0].
    """
    sdh = max(0.0, min(1.0, float(fact.sdh_score)))
    similarity = max(0.0, min(1.0, float(query_similarity)))

    return round(sdh * similarity, 4)


def filter_by_modality(
    facts: Sequence[Fact],
    exclude_modalities: set[str] | None = None,
) -> list[Fact]:
    """Filter out facts whose modality is in the exclusion set."""
    excluded = _get_excluded_modalities(exclude_modalities)

    return [fact for fact in facts if fact.modality not in excluded]


def render_context(facts: Sequence[Fact]) -> str:
    """
    Render packed facts into structured prompt context for local LLMs.

    Preserves:
    - negation
    - adjuncts
    - epistemic modality
    - attribution
    """
    if not facts:
        return ""

    lines: list[str] = []

    for index, fact in enumerate(facts, 1):
        parts = [f"Fact {index}:"]
        parts.extend(_render_fact_parts(fact))
        lines.append(" ".join(parts))

    return "\n".join(lines)


def _estimate_naive_rag_tokens(candidates: Sequence[Fact]) -> int:
    """
    Estimate equivalent naive chunk-based RAG token footprint.

    Standard RAG passes entire retrieved sentences/passages rather than
    atomic facts. Raw sentences are counted once when multiple facts share
    the same sentence.
    """
    seen_sentences: set[str] = set()
    total_tokens = 0

    for fact in candidates:
        if fact.raw_sentence and fact.raw_sentence.strip():
            sentence = fact.raw_sentence.strip()

            if sentence in seen_sentences:
                continue

            seen_sentences.add(sentence)

            words = len(sentence.split())
            total_tokens += max(4, int(words * 1.35))
        else:
            # Fallback when the original sentence was not preserved.
            fact_tokens = estimate_fact_tokens(fact)
            total_tokens += int(fact_tokens * 2.8)

    estimated_fact_tokens = sum(estimate_fact_tokens(fact) for fact in candidates)

    return max(total_tokens, estimated_fact_tokens)


def _empty_pack_result() -> PackResult:
    """Return an empty result for invalid or empty packing requests."""
    return PackResult(
        packed_facts=[],
        tokens_used=0,
        naive_rag_tokens=0,
        compression_rate=0.0,
        avg_sdh_score=0.0,
        facts_considered=0,
        facts_packed=0,
    )


def pack_context(
    query: str,
    store: FactStore,
    token_ceiling: int,
    top_k: int = 100,
    exclude_modalities: set[str] | None = None,
) -> PackResult:
    """
    Execute Stage 4 Context Packing:

    1. Retrieve candidate facts from the vector store by query similarity.
    2. Filter excluded epistemic modalities.
    3. Re-rank surviving candidates using:
           pack_score(t, q) = SDH(t) × query_similarity
    4. Greedily pack highest-scoring facts into the token ceiling.
    5. Compute compression and quality telemetry.
    """
    if not query or not query.strip() or store.count() == 0 or token_ceiling <= 0:
        return _empty_pack_result()

    if top_k <= 0:
        return _empty_pack_result()

    # 1. Retrieve candidates from ChromaDB.
    candidates = store.query_similar(query, n_results=top_k)

    if not candidates:
        return _empty_pack_result()

    all_retrieved_facts = [fact for fact, _ in candidates]
    naive_tokens = _estimate_naive_rag_tokens(all_retrieved_facts)

    # 2. Filter by epistemic modality.
    excluded_modalities = _get_excluded_modalities(exclude_modalities)

    filtered_pairs = [
        (fact, similarity)
        for fact, similarity in candidates
        if fact.modality not in excluded_modalities
    ]

    if not filtered_pairs:
        return PackResult(
            packed_facts=[],
            tokens_used=0,
            naive_rag_tokens=naive_tokens,
            compression_rate=1.0 if naive_tokens > 0 else 0.0,
            avg_sdh_score=0.0,
            facts_considered=0,
            facts_packed=0,
        )

    # 3. Compute pack scores.
    scored_candidates: list[tuple[Fact, float]] = []

    for fact, similarity in filtered_pairs:
        pack_score = compute_pack_score(fact, similarity)
        scored_candidates.append((fact, pack_score))

    # Sort by pack score first. Modality priority breaks score ties.
    scored_candidates.sort(
        key=lambda item: (
            item[1],
            MODALITY_PRIORITY.get(item[0].modality, 0),
        ),
        reverse=True,
    )

    # 4. Greedily pack facts into the token ceiling.
    packed: list[Fact] = []
    tokens_used = 0

    for fact, _ in scored_candidates:
        fact_tokens = estimate_fact_tokens(fact)

        if tokens_used + fact_tokens <= token_ceiling:
            packed.append(fact)
            tokens_used += fact_tokens

    # 5. Compute compression and quality metrics.
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
