import os
import threading
import time
from dataclasses import dataclass

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import spacy  # noqa: E402
from fastcoref import spacy_component  # noqa: E402, F401
from spacy.language import Language  # noqa: E402

from precis.pipeline.hardware import profile_hardware  # noqa: E402

_nlp = None
_nlp_lock = threading.Lock()


@dataclass(slots=True)
class CoreferenceResult:
    text: str
    elapsed: float


def _get_hf_hub_cache() -> str:
    """Return the base directory for Hugging Face Hub caches."""
    if os.environ.get("HF_HUB_CACHE"):
        return os.path.expanduser(os.environ["HF_HUB_CACHE"])
    if os.environ.get("HF_HOME"):
        return os.path.join(os.path.expanduser(os.environ["HF_HOME"]), "hub")
    if os.environ.get("TRANSFORMERS_CACHE"):
        return os.path.expanduser(os.environ["TRANSFORMERS_CACHE"])
    return os.path.expanduser("~/.cache/huggingface/hub")


def _resolve_model_path(model_id: str = "biu-nlp/f-coref") -> str:
    """Resolve a cached Hugging Face model to its local snapshot path."""
    hub_dir = _get_hf_hub_cache()
    repo_dir = os.path.join(hub_dir, f"models--{model_id.replace('/', '--')}")
    refs_main = os.path.join(repo_dir, "refs", "main")

    if not os.path.isfile(refs_main):
        raise FileNotFoundError(
            f"Cached Hugging Face model not found: {model_id}. "
            f"Expected cache at {repo_dir}"
        )

    with open(refs_main, encoding="utf-8") as f:
        revision = f.read().strip()

    if not revision:
        raise FileNotFoundError(
            f"Cached model has an empty main revision: {model_id}"
        )

    snapshot_dir = os.path.join(repo_dir, "snapshots", revision)

    if not os.path.isdir(snapshot_dir):
        raise FileNotFoundError(
            f"Cached model snapshot not found: {snapshot_dir}"
        )

    return snapshot_dir


def _get_nlp() -> Language:
    """Load and return the fastcoref-augmented spaCy pipeline.

    This pipeline excludes the rule-based lemmatizer, ner, and textcat
    components for speed and memory efficiency. It must remain distinct
    from the SVOA pipeline in svoa.py, which explicitly requires the
    lemmatizer for predicate and reporting verb classification.
    """
    global _nlp

    if _nlp is None:
        with _nlp_lock:
            if _nlp is None:
                hardware = profile_hardware()
                device = (
                    "cpu"
                    if hardware.ml_accelerator == "mps"
                    else hardware.ml_accelerator
                )

                _nlp = spacy.load(
                    "en_core_web_lg",
                    exclude=["lemmatizer", "ner", "textcat"],
                )

                model_path = _resolve_model_path("biu-nlp/f-coref")

                _nlp.add_pipe(
                    "fastcoref",
                    config={
                        "model_architecture": "FCoref",
                        "model_path": model_path,
                        "device": device,
                    },
                )

    return _nlp


def resolve_coreferences(text: str) -> str:
    """
    Replace pronouns with their referents throughout the text.

    Input: "Dr. Smith discovered a compound. He published his findings."
    Output: "Dr. Smith discovered a compound. "
            "Dr. Smith published Dr. Smith's findings."
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

        # Look at all mentions in the cluster, not just the representative.
        for start, end in cluster:
            mention = text[start:end]

            # Preserve whitespace around the actual mention.
            l_space = mention[: len(mention) - len(mention.lstrip())]
            r_space = mention[len(mention.rstrip()):]
            mention_clean = mention.strip()

            # Only replace pronouns.
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

    # Replace from the end of the string backwards so offsets stay valid.
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


def _find_representative(
    text: str,
    cluster: list[tuple[int, int]],
) -> str | None:
    """Return the first non-pronoun mention in the cluster."""
    for start, end in cluster:
        mention = text[start:end]

        if mention.strip().lower() not in _PRONOUN_SET:
            return mention

    return None


def _match_case(replacement: str, original: str) -> str:
    if not original:
        return replacement
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
