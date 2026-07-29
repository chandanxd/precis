from __future__ import annotations

from functools import lru_cache

from spacy import load
from spacy.language import Language
from spacy.tokens import Span, Token

from precis.graph.schema import Fact

__all__ = ["extract_facts"]

MODEL_NAME = "en_core_web_lg"


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


def _find_root(sentence: Span) -> Token:
    """Return the root token of a sentence."""
    return sentence.root


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


def _is_copular(root: Token):
    pass


def _extract_copular(
    toor: Token, sentence: Span, source_doc: str, sentence_id: int
) -> Fact | None:
    return


def _extract_svoa(root: Token, sentence: Span, source_doc: str, sentence_id: int) -> Fact | None:
    """Extract SVOA from the obtained results."""
    return
