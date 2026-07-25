import time
from dataclasses import dataclass

import spacy
from fastcoref import spacy_component  # noqa: F401
from spacy.language import Language

from precis.pipeline.hardware import profile_hardware

_nlp = None


@dataclass(slots=True)
class CoreferenceResult:
    text: str
    elapsed: float


def _get_nlp() -> Language:
    global _nlp
    hardware = profile_hardware()
    if _nlp is None:
        device = "cpu" if hardware.ml_accelerator == "mps" else hardware.ml_accelerator
        _nlp = spacy.load("en_core_web_lg", exclude=["lemmatizer", "ner", "textcat"])
        _nlp.add_pipe(
            "fastcoref",
            config={"model_architecture": "FCoref", "device": device},
        )

    return _nlp


def resolve_coreferences(text: str) -> str:
    """
    Replace pronouns with their referents throughout the text

    Input: "Dr. Smith discovered a compound. He published his findings."
    Output: "Dr. Smith discovered a compound. Dr. Smith published his findings."
    """
    nlp = _get_nlp()
    doc = nlp(text)

    clusters = doc._.coref_clusters
    if not clusters:
        return text

    replacements: list[tuple[int, int, str]] = []

    for cluster in clusters:
        representative = _find_representative(text, cluster)
        if representative is None:
            continue

        rep_clean = representative.strip()

        # look at ALL items in the clusters, not just cluster
        for start, end in cluster:
            mention = text[start:end]

            # separate whitespace from the actual word
            l_space = mention[: len(mention) - len(mention.lstrip())]
            r_space = mention[len(mention.rstrip()) :]
            mention_clean = mention.strip()

            # if the mention is not a pronoun, skip it
            if mention_clean.lower() not in _PRONOUN_SET:
                continue

            replacement = _match_case(rep_clean, mention_clean)

            if mention_clean.lower() in _POSSESSIVE_PRONOUNS:
                if rep_clean.endswith("s"):
                    replacement += "'"
                else:
                    replacement += "'s"

            full_replacement = l_space + replacement + r_space

            replacements.append((start, end, full_replacement))

    if not replacements:
        return text

    # replace from end of string backwards so offsets stay valid
    replacements.sort(key=lambda x: x[0], reverse=True)

    result = text
    for start, end, replacement in replacements:
        result = result[:start] + replacement + result[end:]

    return result


_PERSONAL_PRONOUNS = {
    "he",
    "she",
    "it",
    "they",
    "him",
    "her",
    "them",
    "i",
    "me",
    "we",
    "us",
    "you",
}

_POSSESSIVE_PRONOUNS = {
    "his",
    "her",
    "hers",
    "its",
    "their",
    "theirs",
    "my",
    "mine",
    "our",
    "ours",
    "your",
    "yours",
}

_REFLEXIVE_PRONOUNS = {
    "myself",
    "yourself",
    "yourselves",
    "himself",
    "herself",
    "itself",
    "ourselves",
    "themselves",
}

_PRONOUN_SET = _PERSONAL_PRONOUNS | _POSSESSIVE_PRONOUNS | _REFLEXIVE_PRONOUNS


def _find_representative(text: str, cluster: list[tuple[int, int]]) -> str | None:
    """Return the first non-pronoun mention in the cluster"""

    for start, end in cluster:
        mention = text[start:end]

        if mention.strip().lower() not in _PRONOUN_SET:
            return mention

    if cluster:
        start, end = cluster[0]
        return text[start:end]

    return None


def _match_case(replacement: str, original: str) -> str:
    if original.isupper():
        return replacement.upper()
    if original[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement


def resolve_document(text: str) -> CoreferenceResult:
    start = time.perf_counter()

    resolved = resolve_coreferences(text)
    elapsed = time.perf_counter() - start
    return CoreferenceResult(text=resolved, elapsed=elapsed)
