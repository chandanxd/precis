"""
Exact Match (EM), ROUGE-L, token F1, and semantic similarity metrics
for document question answering evaluation.

The evaluation layer is designed to work in offline CPU environments.

Metrics:
- Exact Match (EM): normalized string equality.
- Token F1: token-level overlap between prediction and reference.
- ROUGE-L: longest common subsequence F1.
- BERTScore: optional model-based BERTScore using DeBERTa.
- Embedding similarity: offline-first MiniLM cosine similarity fallback.

When DeBERTa BERTScore is unavailable or disabled, `compute_bert_score`
falls back to embedding cosine similarity. The fallback is intentionally
documented as semantic similarity rather than being treated as equivalent
to canonical BERTScore.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from typing import Any, cast

# Lazy-loaded ROUGE scorer.
_rouge_scorer = None


def _validate_text(value: str, name: str) -> None:
    """Validate that a metric input is a string."""

    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string, got {type(value).__name__}.")


def normalize_answer(text: str) -> str:
    """
    Normalize an answer for QA-style lexical comparison.

    Normalization:
    - Lowercase.
    - Strip leading/trailing whitespace.
    - Remove English articles: a, an, the.
    - Remove punctuation.
    - Collapse repeated whitespace.
    """

    _validate_text(text, "text")

    if not text:
        return ""

    text = text.lower().strip()

    # Remove articles before punctuation normalization so that article
    # boundaries remain straightforward to detect.
    text = re.sub(r"\b(a|an|the)\b", " ", text)

    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def compute_exact_match(
    predicted: str,
    gold: str,
) -> bool:
    """
    Compute Exact Match (EM).

    Returns True when the normalized prediction exactly matches the
    normalized reference answer.
    """

    norm_predicted = normalize_answer(predicted)
    norm_gold = normalize_answer(gold)

    return norm_predicted == norm_gold


def compute_token_f1(
    predicted: str,
    gold: str,
) -> float:
    """
    Compute token-level F1.

    Tokens are produced using the same normalization as Exact Match.
    Duplicate tokens are counted using multiset intersection.
    """

    pred_tokens = normalize_answer(predicted).split()
    gold_tokens = normalize_answer(gold).split()

    if not pred_tokens or not gold_tokens:
        return float(pred_tokens == gold_tokens)

    pred_counts = Counter(pred_tokens)
    gold_counts = Counter(gold_tokens)

    num_same = sum((pred_counts & gold_counts).values())

    if num_same == 0:
        return 0.0

    precision = num_same / len(pred_tokens)
    recall = num_same / len(gold_tokens)

    if precision + recall == 0.0:
        return 0.0

    f1 = 2.0 * precision * recall / (precision + recall)

    return round(f1, 4)


def compute_rouge_l(
    predicted: str,
    gold: str,
) -> float:
    """
    Compute ROUGE-L F1 using `rouge-score`.

    ROUGE-L measures longest common subsequence overlap between
    the predicted and reference answers.
    """

    _validate_text(predicted, "predicted")
    _validate_text(gold, "gold")

    if not predicted or not gold:
        return 0.0

    global _rouge_scorer

    if _rouge_scorer is None:
        try:
            from rouge_score import rouge_scorer
        except ImportError as exc:
            raise RuntimeError(
                "ROUGE-L requires the 'rouge-score' package. "
                "Install it with: pip install rouge-score"
            ) from exc

        _rouge_scorer = rouge_scorer.RougeScorer(
            ["rougeL"],
            use_stemmer=True,
        )

    scores = _rouge_scorer.score(
        gold.strip(),
        predicted.strip(),
    )

    return round(
        float(scores["rougeL"].fmeasure),
        4,
    )


def compute_embedding_similarity(
    predicted: str,
    gold: str,
) -> float:
    """
    Compute semantic similarity using the cached MiniLM embeddings
    already used by Précis' SDH layer.

    This is not canonical BERTScore. It is an offline-friendly
    cosine-similarity fallback for environments where the full
    BERTScore model is unavailable.
    """

    _validate_text(predicted, "predicted")
    _validate_text(gold, "gold")

    if not predicted or not gold:
        return 0.0

    from precis.pipeline.sdh import (
        cosine_similarity,
        embed_text,
    )

    predicted_embedding = embed_text(predicted.strip())
    gold_embedding = embed_text(gold.strip())

    similarity = cosine_similarity(
        predicted_embedding,
        gold_embedding,
    )

    return round(
        float(
            max(
                0.0,
                min(1.0, similarity),
            )
        ),
        4,
    )


def compute_bert_score(
    predicted: str,
    gold: str,
    model_type: str = "microsoft/deberta-xlarge-mnli",
) -> float:
    """
    Compute semantic similarity for evaluation.

    When PRECIS_USE_DEBERTA_BERTSCORE=1 is set, this attempts to use
    canonical BERTScore with the configured DeBERTa model.

    Otherwise, or when the requested BERTScore backend cannot be
    loaded, it falls back to MiniLM embedding cosine similarity.

    Important:
        The fallback is NOT mathematically equivalent to BERTScore.
        It is an offline semantic-similarity substitute.
    """

    _validate_text(predicted, "predicted")
    _validate_text(gold, "gold")

    if not predicted or not gold:
        return 0.0

    use_deberta = os.environ.get("PRECIS_USE_DEBERTA_BERTSCORE") == "1"

    if use_deberta:
        try:
            from bert_score import score as bert_score_fn
        except ImportError:
            # The optional dependency is not installed.
            return compute_embedding_similarity(
                predicted,
                gold,
            )

        try:
            os.environ.setdefault(
                "MPLCONFIGDIR",
                "/tmp/matplotlib",
            )

            scores = bert_score_fn(
                [predicted.strip()],
                [gold.strip()],
                lang="en",
                model_type=model_type,
                verbose=False,
            )

            f1 = cast(Any, scores[2])

            return round(
                float(f1.mean().item()),
                4,
            )

        except (
            OSError,
            RuntimeError,
            ValueError,
        ):
            # Model loading can fail in offline environments when the
            # requested Hugging Face model is not already cached.
            return compute_embedding_similarity(
                predicted,
                gold,
            )

    return compute_embedding_similarity(
        predicted,
        gold,
    )
