from dataclasses import dataclass, field

@dataclass
class Fact:
    subject: str
    verb: str
    object: str
    adjuncts: dict[str, str] = field(default_factory=dict)
    negated: bool = False
    modality: str = "asserted" # asserted | conditional | attributed | hypothetical
    attributed_to: str | None = None
    disjnctive: bool = False
    sdh_score: float = 0.0
    embedding: list[float] = field(default_factory=list)
    source_doc: str = ""
    sentence_id: int = 0
