import spacy
from fastcoref import spacy_component  # noqa: F401
from spacy.language import Language

from precis.pipeline.hardware import profile_hardware

_nlp = None


def _get_nlp() -> Language:
    global _nlp
    hardware = profile_hardware()
    if _nlp is None:
        _nlp = spacy.load(
            "en_core_web_lg", exclude=["parser", "lemmatizer", "ner", "textcat"]
        )
        _nlp.add_pipe(
            "fastcoref",
            config={"model_architecture": "FCoref", "device": hardware.ml_accelerator},
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

    print(doc._.coref_clusters)
    for cluster in doc._.coref_clusters:
        print("Cluster:")
        for start, end in cluster:
            print(repr(text[start:end]))

    clusters = doc._.coref_clusters
    if not clusters:
        return text

    replacements: list[tuple[int, int, str]] = []

    for cluster in clusters:
        representative = _find_representative(text, cluster)
        if representative is None:
            continue

        # skip the representative mention itself
        for start, end in cluster[1:]:
            mention = text[start:end]

            if mention.lower() not in _PRONOUN_SET:
                continue
            replacement = _match_case(representative, mention)

            if mention.lower() in _POSSESSIVE_PRONOUNS:
                if representative.endswith("s"):
                    replacement += "'"
                else:
                    replacement += "'s"

            replacements.append((start, end, replacement))

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
    """return the first pronoun mention in the cluster"""

    for start, end in cluster:
        mention = text[start:end]

        if mention.lower() not in _PRONOUN_SET:
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
    return replacement.lower()
