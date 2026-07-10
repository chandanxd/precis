import spacy
from spacy.language import Language

from precis.pipeline.hardware import profile_hardware

_nlp = None


def _get_nlp() -> Language:
    global _nlp
    hardware = profile_hardware()
    if _nlp is None:
        _nlp = spacy.load(
            "en-core-web-lg", exclude=["parser", "lemmatizer", "ner", "textcat"]
        )
        _nlp.add_pipe(
            "fastcoref",
            config={"model_architecture": "FCoref", "device": hardware.ml_accelerator},
        )
    return _nlp
