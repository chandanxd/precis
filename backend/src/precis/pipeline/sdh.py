"""
Computes a four-term information density score for each extracted SVOA fact:
    SDH(t) = α·E(s,o) + β·I(v) + γ·U(t,G) + δ·A(t)

Where:
    - E(s,o): Entity relatedness / salience (subject-object cosine similarity & specificity)
    - I(v):   Verb informativeness (inverse-frequency / Zipf rank of lexical head verb)
    - U(t,G): Uniqueness relative to existing fact embeddings (cold start = 1.0)
    - A(t):   Adjunct density (weighted contextual qualifiers: cause, time, location, manner)

All scores are bounded in [0.0, 1.0].
"""

import os
import re
from collections.abc import Sequence
from typing import Any, cast

import numpy as np
from sentence_transformers import SentenceTransformer

from precis.graph.schema import Fact
from precis.pipeline.svoa import get_nlp

# Lazy-loaded sentence transformer embedding model
_embedding_model: SentenceTransformer | None = None

_UINT64_MAX = 2**64 - 1

DEFAULT_WEIGHTS: dict[str, float] = {
    "alpha": 0.25,  # E(s,o): Entity relatedness
    "beta": 0.25,  # I(v): Verb informativeness
    "gamma": 0.25,  # U(t,G): Uniqueness
    "delta": 0.25,  # A(t): Adjunct density
}

ABLATION_DROP_ALPHA: dict[str, float] = {
    "alpha": 0.0,
    "beta": 1.0 / 3.0,
    "gamma": 1.0 / 3.0,
    "delta": 1.0 / 3.0,
}

ABLATION_DROP_BETA: dict[str, float] = {
    "alpha": 1.0 / 3.0,
    "beta": 0.0,
    "gamma": 1.0 / 3.0,
    "delta": 1.0 / 3.0,
}

ABLATION_DROP_GAMMA: dict[str, float] = {
    "alpha": 1.0 / 3.0,
    "beta": 1.0 / 3.0,
    "gamma": 0.0,
    "delta": 1.0 / 3.0,
}

ABLATION_DROP_DELTA: dict[str, float] = {
    "alpha": 1.0 / 3.0,
    "beta": 1.0 / 3.0,
    "gamma": 1.0 / 3.0,
    "delta": 0.0,
}

# Categorized verb tiers for informativeness calibration
_LIGHT_COPULAR_LEMMAS = {
    "be",
    "have",
    "do",
    "seem",
    "become",
    "appear",
    "get",
    "make",
    "go",
    "come",
    "take",
    "give",
    "let",
    "keep",
    "put",
}

_REPORTING_COMMON_LEMMAS = {
    "say",
    "tell",
    "state",
    "mention",
    "think",
    "know",
    "see",
    "find",
    "use",
    "show",
    "call",
    "ask",
    "feel",
    "try",
    "leave",
}

_GENERIC_PRONOUNS = {
    "it",
    "they",
    "them",
    "he",
    "she",
    "him",
    "her",
    "someone",
    "somebody",
    "something",
    "anything",
    "anyone",
    "nothing",
    "this",
    "that",
    "these",
    "those",
}

_ADJUNCT_TYPE_WEIGHTS = {
    "cause": 1.2,
    "time": 1.0,
    "loc": 0.9,
    "manner": 0.8,
}


def get_embedding_model() -> SentenceTransformer:
    """Lazy-load the SentenceTransformer embedding model in offline mode."""
    global _embedding_model
    if _embedding_model is None:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        _embedding_model = SentenceTransformer(
            "all-MiniLM-L6-v2", local_files_only=True
        )
    return _embedding_model


def embed_text(text: str) -> list[float]:
    """Embed a single text string into a 384-dimensional vector."""
    if not text or not text.strip():
        return [0.0] * 384
    model = get_embedding_model()
    vec = model.encode(text.strip(), show_progress_bar=False, normalize_embeddings=True)
    return vec.tolist()


def embed_texts(texts: Sequence[str], batch_size: int = 64) -> list[list[float]]:
    """Batch embed multiple text strings into normalized vectors."""
    if not texts:
        return []
    clean_texts = [t.strip() if t and t.strip() else " " for t in texts]
    model = get_embedding_model()
    vecs = model.encode(
        clean_texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return vecs.tolist()


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Compute cosine similarity between two vectors."""
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    norm_a = float(np.linalg.norm(va))
    norm_b = float(np.linalg.norm(vb))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def canonical_fact_text(fact: Fact) -> str:
    """
    Format a complete textual representation of the fact including
    negation and adjuncts so uniqueness distinguishes variants.
    """
    parts: list[str] = []
    if fact.subject:
        parts.append(fact.subject.strip())
    if fact.negated:
        parts.append("does not")
    if fact.verb:
        parts.append(fact.verb.strip())
    if fact.object:
        parts.append(fact.object.strip())

    if isinstance(fact.adjuncts, dict):
        for k in sorted(fact.adjuncts.keys()):
            vals = fact.adjuncts[k]
            if isinstance(vals, list):
                for val in vals:
                    if val:
                        parts.append(f"({k}: {val.strip()})")
            elif isinstance(vals, str) and vals:
                parts.append(f"({k}: {vals.strip()})")

    if fact.modality and fact.modality != "asserted":
        parts.append(f"[{fact.modality}]")
    if fact.attributed_to:
        parts.append(f"[attributed: {fact.attributed_to.strip()}]")

    return " ".join(parts).strip()


# Term 1: E(s,o): Entity Relatedness / Salience


def entity_relatedness(
    fact: Fact,
    s_emb: Sequence[float] | None = None,
    o_emb: Sequence[float] | None = None,
) -> float:
    """
    E(s,o): Entity relatedness and information salience.
    Measures semantic affinity between subject and object, with a penalty
    for generic pronouns/placeholders and calibration to preserve
    scores for informative complementary entities.
    """
    s = fact.subject.strip() if fact.subject else ""
    o = fact.object.strip() if fact.object else ""

    if not s or not o:
        return 0.0

    if s_emb is None:
        s_emb = embed_text(s)
    if o_emb is None:
        o_emb = embed_text(o)

    raw_sim = max(0.0, cosine_similarity(s_emb, o_emb))

    # Entity informativeness discount if subject or object is a generic pronoun
    s_words = set(re.findall(r"\w+", s.lower()))
    o_words = set(re.findall(r"\w+", o.lower()))

    penalty = 1.0
    if s_words and s_words.issubset(_GENERIC_PRONOUNS):
        penalty *= 0.7
    if o_words and o_words.issubset(_GENERIC_PRONOUNS):
        penalty *= 0.7

    # Calibrate cosine similarity so complementary domain entities (sim ~0.35-0.5)
    # are recognized as informative relationships rather than collapsing to near 0.
    # Scaled affine map: [0.15, 0.85] -> [0.20, 1.0]
    if raw_sim < 0.15:
        calibrated = raw_sim * (0.20 / 0.15)
    else:
        calibrated = 0.20 + 0.80 * min(1.0, (raw_sim - 0.15) / 0.70)

    score = calibrated * penalty
    return round(float(np.clip(score, 0.0, 1.0)), 4)


# Term 2: I(v): Verb Informativeness


def _extract_head_verb_lemma(verb_phrase: str) -> tuple[str, bool]:
    """
    Decompose a multi-word verb phrase into its primary lexical head lemma.
    Returns (lemma, is_passive_or_copular).
    """
    if not verb_phrase or not verb_phrase.strip():
        return "", True

    cleaned = verb_phrase.strip()
    nlp = get_nlp()
    doc = nlp(cleaned)

    # Find the main lexical verb or the ROOT
    head_token = None
    # 1. Prefer tokens with pos_ == "VERB" that are not auxiliaries
    verbs = [t for t in doc if t.pos_ == "VERB"]
    if verbs:
        # If there are multiple verbs (e.g. "started running"), take the most content-bearing one
        head_token = verbs[-1]
    else:
        # Fallback to ROOT or AUX
        for token in doc:
            if token.dep_ == "ROOT" or token.pos_ in {"AUX", "VERB"}:
                head_token = token
                break

    if head_token is None and len(doc) > 0:
        head_token = doc[-1]

    if head_token is None:
        return "", True

    lemma = head_token.lemma_.lower()
    is_light = lemma in _LIGHT_COPULAR_LEMMAS
    return lemma, is_light


def verb_informativeness(fact: Fact) -> float:
    """
    I(v): Verb informativeness via head lemma inverse-frequency calibration.
    Light/copular verbs (is, has, does, make) receive low informativeness (0.20-0.35).
    Common communicative/reporting verbs receive medium scores (0.45-0.60).
    Specific action and domain-specific verbs receive high scores (0.75-0.95).
    """
    verb_str = fact.verb.strip() if fact.verb else ""
    if not verb_str:
        return 0.10

    lemma, is_light = _extract_head_verb_lemma(verb_str)
    if not lemma:
        return 0.15

    # Tier 1: Light / Copular / Auxiliary verbs
    if is_light or lemma in _LIGHT_COPULAR_LEMMAS:
        if lemma in {"be", "is", "was", "are", "were"}:
            return 0.20
        if lemma in {"have", "has", "had", "do", "did"}:
            return 0.25
        return 0.32

    # Tier 2: Common reporting / perception / generic verbs
    if lemma in _REPORTING_COMMON_LEMMAS:
        return 0.50

    # Tier 3 & 4: Use spaCy vocabulary rank and stopword cues
    nlp = get_nlp()
    lex = nlp.vocab[lemma]

    if lex.is_stop:
        return 0.35

    if lex.is_oov:
        # OOV verbs in en_core_web_lg are typically highly domain-specific
        return 0.85

    # In spaCy en_core_web_lg, vectors cover ~342,918 words.
    # Words are ordered in the vector table such that higher rank indicates a less frequent word.
    vector_count = len(nlp.vocab.vectors)

    if vector_count == 0:
        max_rank = 342_918
    else:
        max_rank = vector_count

    if lex.rank == _UINT64_MAX:
        rank = max_rank
    elif lex.rank > 0:
        rank = min(lex.rank, max_rank)
    else:
        rank = max_rank // 2

    # Smooth non-linear informativeness curve
    normalized = min(1.0, rank / max_rank)
    # Base informativeness for non-stop action verbs starts at 0.58 and scales to 0.98
    score = 0.58 + 0.40 * (normalized**0.5)
    return round(float(np.clip(score, 0.0, 1.0)), 4)


# Term 3: U(t,G): Uniqueness / Novelty


def uniqueness(
    fact: Fact,
    existing_embeddings: Sequence[Sequence[float]] | np.ndarray | None = None,
    fact_emb: Sequence[float] | None = None,
    soft_threshold: bool = True,
) -> float:
    """
    U(t,G): Novelty of fact relative to the existing graph/store.
    Cold-start rule: U(t, ∅) = 1.0 by definition.

    Uses soft-threshold redundancy penalty:
    - Cosine similarity < 0.60: full uniqueness (1.0). Distinct assertions on same topic.
    - Cosine similarity 0.60 - 0.88: gradual penalty transition.
    - Cosine similarity > 0.88: near duplicate, uniqueness drops towards 0.0.
    """
    if existing_embeddings is None or len(existing_embeddings) == 0:
        return 1.0

    if fact_emb is None:
        if fact.embedding and len(fact.embedding) == 384:
            fact_emb = fact.embedding
        else:
            fact_emb = embed_text(canonical_fact_text(fact))
            fact.embedding = fact_emb

    v = np.asarray(fact_emb, dtype=np.float32)
    v_norm = float(np.linalg.norm(v))
    if v_norm == 0.0:
        return 1.0
    v = v / v_norm

    mat = np.asarray(existing_embeddings, dtype=np.float32)
    mat_norms = np.linalg.norm(mat, axis=1, keepdims=True)
    mat_norms = np.maximum(mat_norms, 1e-8)
    norm_mat = mat / mat_norms

    # Vectorized cosine similarities
    sims = np.dot(norm_mat, v)
    max_sim = float(np.max(sims))

    if not soft_threshold:
        return round(float(np.clip(1.0 - max_sim, 0.0, 1.0)), 4)

    if max_sim <= 0.60:
        u = 1.0
    elif max_sim >= 0.92:
        u = max(0.0, (1.0 - max_sim) / 0.08 * 0.15)
    else:
        # Smooth cosine interpolation between 0.60 and 0.92
        progress = (max_sim - 0.60) / (0.92 - 0.60)
        u = 1.0 - 0.85 * (progress**1.5)

    return round(float(np.clip(u, 0.0, 1.0)), 4)


# Term 4: A(t): Adjunct Density / Context Richness


def adjunct_density(fact: Fact) -> float:
    """
    A(t): Contextual richness provided by temporal, spatial, and causal qualifiers.
    Provides a baseline score (0.20) for concise atomic facts, scaling up to 1.0
    with type-weighted qualifiers (cause and time weighted highest).
    """
    if not fact.adjuncts or not isinstance(fact.adjuncts, dict):
        return 0.20

    weighted_count = 0.0
    total_qualifiers = 0

    for adj_type, val in fact.adjuncts.items():
        w = _ADJUNCT_TYPE_WEIGHTS.get(adj_type.lower(), 0.8)
        if isinstance(val, list):
            count = len([x for x in val if x and str(x).strip()])
            weighted_count += w * count
            total_qualifiers += count
        elif isinstance(val, str) and val.strip():
            weighted_count += w * 1.0
            total_qualifiers += 1

    if total_qualifiers == 0:
        return 0.20

    # Base presence (0.20) + up to 0.80 based on qualifiers
    # 3+ weighted qualifiers reaches 1.0
    score = 0.20 + 0.80 * min(1.0, weighted_count / 3.0)
    return round(float(np.clip(score, 0.0, 1.0)), 4)


# Composite SDH Scoring


def score_fact(
    fact: Fact,
    existing_embeddings: Sequence[Sequence[float]] | np.ndarray | None = None,
    weights: dict[str, float] | None = None,
    fact_emb: Sequence[float] | None = None,
    s_emb: Sequence[float] | None = None,
    o_emb: Sequence[float] | None = None,
    soft_uniqueness: bool = True,
) -> float:
    """
    Compute SDH score for a single fact.

        SDH(t) = α·E(s,o) + β·I(v) + γ·U(t,G) + δ·A(t)

    Weights are normalized so their sum equals 1.0.
    Returns float bounded in [0.0, 1.0].
    """
    w = weights if weights is not None else DEFAULT_WEIGHTS
    total_w = sum(w.values())
    if total_w <= 0.0:
        w_norm = DEFAULT_WEIGHTS
    else:
        w_norm = {k: v / total_w for k, v in w.items()}

    alpha = w_norm.get("alpha", 0.25)
    beta = w_norm.get("beta", 0.25)
    gamma = w_norm.get("gamma", 0.25)
    delta = w_norm.get("delta", 0.25)

    e = entity_relatedness(fact, s_emb=s_emb, o_emb=o_emb) if alpha > 0.0 else 0.0
    i = verb_informativeness(fact) if beta > 0.0 else 0.0
    u = (
        uniqueness(
            fact,
            existing_embeddings=existing_embeddings,
            fact_emb=fact_emb,
            soft_threshold=soft_uniqueness,
        )
        if gamma > 0.0
        else 0.0
    )
    a = adjunct_density(fact) if delta > 0.0 else 0.0

    score = alpha * e + beta * i + gamma * u + delta * a
    fact.sdh_score = round(float(np.clip(score, 0.0, 1.0)), 4)
    return fact.sdh_score


def score_facts(
    facts: list[Fact],
    existing_embeddings: Sequence[Sequence[float]] | np.ndarray | None = None,
    weights: dict[str, float] | None = None,
    batch_size: int = 64,
    soft_uniqueness: bool = True,
) -> list[Fact]:
    """
    Score all facts in a list with batched vectorization.
    Updates each fact's sdh_score in place and caches its embedding in fact.embedding.

    Uniqueness is computed sequentially: each fact is evaluated against
    both prior store embeddings and the facts preceding it in the batch.
    """
    if not facts:
        return []

    # 1. Batch encode all canonical fact representations
    canonical_texts = [canonical_fact_text(f) for f in facts]
    fact_embeddings = embed_texts(canonical_texts, batch_size=batch_size)

    # 2. Extract and batch-embed unique subjects and objects
    subjects = [f.subject.strip() for f in facts if f.subject]
    objects = [f.object.strip() for f in facts if f.object]
    unique_entities = list(dict.fromkeys(subjects + objects))
    entity_vectors = embed_texts(unique_entities, batch_size=batch_size)
    entity_emb_map = {ent: vec for ent, vec in zip(unique_entities, entity_vectors)}

    # 3. Initialize accumulated embeddings list for sequential uniqueness
    accumulated_embs: list[Sequence[float]] = []
    if existing_embeddings is not None and len(existing_embeddings) > 0:
        if isinstance(existing_embeddings, np.ndarray):
            existing = cast(list[list[float]], existing_embeddings.tolist())
        else:
            existing = existing_embeddings
        accumulated_embs.extend(existing)

    # 4. Score each fact
    for i, fact in enumerate(facts):
        f_emb = fact_embeddings[i]
        fact.embedding = f_emb

        s_clean = fact.subject.strip() if fact.subject else ""
        o_clean = fact.object.strip() if fact.object else ""
        s_emb = entity_emb_map.get(s_clean)
        o_emb = entity_emb_map.get(o_clean)

        score_fact(
            fact=fact,
            existing_embeddings=accumulated_embs,
            weights=weights,
            fact_emb=f_emb,
            s_emb=s_emb,
            o_emb=o_emb,
            soft_uniqueness=soft_uniqueness,
        )

        accumulated_embs.append(f_emb)

    return facts


def score_facts_with_store(
    facts: list[Fact],
    store: Any,
    weights: dict[str, float] | None = None,
    batch_size: int = 64,
    soft_uniqueness: bool = True,
) -> list[Fact]:
    """
    Score facts using the embeddings already in ChromaDB FactStore for U(t,G).
    This is the production integration path used in the orchestrator.
    """
    existing: list[list[float]] = []
    if store is not None and hasattr(store, "get_all_embeddings"):
        existing = store.get_all_embeddings()
    return score_facts(
        facts=facts,
        existing_embeddings=existing,
        weights=weights,
        batch_size=batch_size,
        soft_uniqueness=soft_uniqueness,
    )
