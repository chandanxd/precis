from __future__ import annotations

from functools import lru_cache

from spacy import load
from spacy.language import Language
from spacy.tokens import Span, Token

from precis.graph.schema import Fact

__all__ = ["extract_facts"]

MODEL_NAME = "en_core_web_lg"


# Lexical resources

_COPULAR_VERBS = {"be", "become", "appear", "remain", "seem"}
_NEGATION_CUES = {"not", "never", "no", "neither", "nor", "n't", "cannot"}
_TEMPORAL_MARKERS = {"on", "in", "during", "after", "before", "since", "until", "by"}
_SPATIAL_MARKERS = {"in", "at", "near", "from", "to", "across", "through"}
_CAUSAL_MARKERS = {"because", "due", "since", "as", "owing"}


@lru_cache(maxsize=1)
def get_nlp() -> Language:
    """Load and cache the spaCy pipeline."""
    try:
        return load(MODEL_NAME)
    except OSError as exc:
        raise RuntimeError(
            f"spaCy model '{MODEL_NAME}' is not installed. "
            f"Install it with: python -m spacy download {MODEL_NAME}"
        ) from exc


def extract_facts(text: str, source_doc: str = "") -> list[Fact]:
    """
    Extract Fact objects from coreference-resolved English text.

    The input is expected to be the output of Stage 1 (coreference resolution).
    A sentence may produce zero or more facts.
    """
    if not text.strip():
        return []

    doc = get_nlp()(text)
    facts: list[Fact] = []

    for sentence_id, sentence in enumerate(doc.sents):
        sentence_facts = _extract_from_sentence(sentence, source_doc, sentence_id)
        facts.extend(sentence_facts)

    return facts


def _extract_from_sentence(
    sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """Extract all facts from a single sentence."""
    root = _find_root(sentence)

    facts: list[Fact] = []

    # primary SVOA proposition
    primary = _extract_primary_fact(root, sentence, source_doc, sentence_id)
    if primary is not None:
        facts.append(primary)

    # additional propositions
    facts.extend(_extract_coordination(root, sentence, source_doc, sentence_id))

    facts.extend(_extract_relative_clauses(sentence, source_doc, sentence_id))

    return facts


def _extract_primary_fact(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> Fact | None:
    """Extract the primary SVOA fact from a sentence."""

    if _is_copular(root):
        return _extract_copular(root, sentence, source_doc, sentence_id)

    return _extract_svoa(root, sentence, source_doc, sentence_id)


# Sentence helpers

def _find_root(sentence: Span) -> Token:
    """Return the root token of a sentence."""
    return sentence.root


# Lexical helpers

def _is_copular(root: Token) -> bool:
    """Return whether the root is a copular verb."""
    return root.lemma_ in _COPULAR_VERBS


def _is_negated(root: Token) -> bool:
    """Return whether the predicate is negated."""
    for child in root.children:
        if child.dep_ == "neg":
            return True

        if child.text.lower() in _NEGATION_CUES:
            return True

        if child.dep_ == "aux" and child.text.lower().endswith("n't"):
            return True

    return False


# Span helpers

def _get_span_text(token: Token) -> str:
    """Return the text spanned by a token's subtree."""
    return token.doc[token.left_edge.i : token.right_edge.i + 1].text


def _get_prepositional_phrase(preposition: Token) -> str:
    """Return the full text of a prepositional phrase."""
    return preposition.doc[preposition.left_edge.i : preposition.right_edge.i + 1].text


# Argument helpers

def _get_subject(root: Token) -> str | None:
    """Return the sentence subject, if present."""
    for child in root.children:
        if child.dep_ in {"nsubj", "nsubjpass"}:
            return _get_span_text(child)
    return None


def _get_object(root: Token) -> str | None:
    """Return the direct object, if present."""
    for child in root.children:
        if child.dep_ == "obj":
            return _get_span_text(child)
    return None


def _get_agent(root: Token) -> str | None:
    """Return the agent of a passive construction, if present."""
    for child in root.children:
        if child.dep_ == "agent":
            for grandchild in child.children:
                if grandchild.dep_ == "pobj":
                    return _get_span_text(grandchild)

        if child.dep_ == "prep" and child.text.lower() == "by":
            for grandchild in child.children:
                if grandchild.dep_ == "pobj":
                    return _get_span_text(grandchild)

    return None


# Predicate helpers

def _get_verb_phrase(root: Token) -> str:
    """Return the verb phrase headed by the root."""
    parts: list[str] = []

    for child in sorted(root.children, key=lambda t: t.i):
        if child.dep_ == "aux" and child.i < root.i:
            parts.append(child.text)

    parts.append(root.text)

    for child in sorted(root.children, key=lambda t: t.i):
        if child.dep_ == "prt":
            parts.append(child.text)

    return " ".join(parts)


def _extract_copular(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> Fact | None:
    return


def _extract_svoa(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> Fact | None:
    """Extract SVOA from the obtained results."""
    return


def _extract_coordination(
    root: Token, sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """Extract facts from coordinated clauses."""
    return []


def _extract_relative_clauses(
    sentence: Span, source_doc: str, sentence_id: int
) -> list[Fact]:
    """Extract facts from relative clauses."""
    return []

