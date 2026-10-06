"""
Exact Match (EM), ROUGE-L, token F1, and semantic similarity metrics
for document question answering evaluation.

The evaluation layer is designed to work in offline CPU environments.

Metrics:
- Exact Match (EM): normalized string equality.
- Token F1: token-level overlap between prediction and reference.
- ROUGE-L: longest common subsequence F1.
- BERTScore: genuine token-level contextual BERTScore using DeBERTa.
- MiniLM Cosine: sentence-embedding cosine similarity using all-MiniLM-L6-v2.

Genuine BERTScore and MiniLM cosine similarity are strictly separated:
`compute_bert_score` never silently falls back to sentence embeddings.
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


DEFAULT_BERTSCORE_MODEL = "microsoft/deberta-large-mnli"
DEFAULT_BERTSCORE_BATCH_SIZE = 4


def is_bertscore_model_cached(
    model_type: str = DEFAULT_BERTSCORE_MODEL,
) -> bool:
    """Check if the requested model is locally available without network access."""
    if os.path.isdir(model_type) and os.path.isfile(os.path.join(model_type, "config.json")):
        return True

    hf_cache = os.environ.get("HF_HUB_CACHE")
    if not hf_cache:
        hf_home = os.environ.get("HF_HOME")
        if hf_home:
            hf_cache = os.path.join(os.path.expanduser(hf_home), "hub")
        else:
            hf_cache = os.path.expanduser("~/.cache/huggingface/hub")

    repo_dir = os.path.join(hf_cache, f"models--{model_type.replace('/', '--')}")
    refs_main = os.path.join(repo_dir, "refs", "main")
    if os.path.isfile(refs_main):
        try:
            with open(refs_main, "r", encoding="utf-8") as f:
                rev = f.read().strip()
            if rev and os.path.isdir(os.path.join(repo_dir, "snapshots", rev)):
                return True
        except OSError:
            pass

    snapshots_dir = os.path.join(repo_dir, "snapshots")
    if os.path.isdir(snapshots_dir):
        try:
            for snap in os.listdir(snapshots_dir):
                if os.path.isfile(os.path.join(snapshots_dir, snap, "config.json")):
                    return True
        except OSError:
            pass

    return False


def compute_minilm_cosine(
    predicted: str,
    gold: str,
) -> float:
    """
    Compute sentence-level semantic similarity using MiniLM embeddings.

    Important:
        This is sentence-embedding cosine similarity using all-MiniLM-L6-v2.
        It is NOT BERTScore (which performs greedy token-level alignment over
        contextual token embeddings from DeBERTa/BERT).
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


# Backward-compatible alias for existing callers.
compute_embedding_similarity = compute_minilm_cosine


def compute_bert_score(
    predicted: str,
    gold: str,
    model_type: str = DEFAULT_BERTSCORE_MODEL,
    device: str | None = None,
    batch_size: int = DEFAULT_BERTSCORE_BATCH_SIZE,
) -> float:
    """
    Compute genuine BERTScore F1 using token-level contextual representations.

    Parameters:
    - predicted: The candidate answer string.
    - gold: The ground-truth reference answer string.
    - model_type: Pretrained model identifier (default: microsoft/deberta-large-mnli).
    - device: "cuda" or "cpu" (auto-detected if None).
    - batch_size: Batch size for token embedding generation (default: 4).

    Important:
    - This function computes actual BERTScore using `bert_score.score()`.
    - It does NOT fall back to sentence-level cosine similarity.
    - If the model is not cached locally in offline mode, or the `bert-score`
      package is missing, an explicit exception is raised.
    """
    _validate_text(predicted, "predicted")
    _validate_text(gold, "gold")

    if not predicted or not gold:
        return 0.0

    try:
        from bert_score import score as bert_score_fn
    except ImportError as exc:
        raise RuntimeError(
            "Genuine BERTScore requires the 'bert-score' package. "
            "Install it with: pip install bert-score"
        ) from exc

    is_offline = (
        os.environ.get("HF_HUB_OFFLINE") == "1"
        or os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    )
    if is_offline and not is_bertscore_model_cached(model_type):
        raise FileNotFoundError(
            f"BERTScore model '{model_type}' is not cached locally for offline execution. "
            "Pre-cache the model before running offline benchmarks."
        )

    if device is None:
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"

    os.environ.setdefault(
        "MPLCONFIGDIR",
        "/tmp/matplotlib",
    )

    scores = bert_score_fn(
        [predicted.strip()],
        [gold.strip()],
        lang="en",
        model_type=model_type,
        device=device,
        batch_size=batch_size,
        verbose=False,
    )

    f1 = cast(Any, scores[2])

    return round(
        float(f1.mean().item()),
        4,
    )
