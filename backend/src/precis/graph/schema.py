from dataclasses import dataclass, field


@dataclass
class Fact:
    subject: str
    verb: str
    object: str

    adjuncts: dict[str, list[str]] = field(default_factory=dict)

    negated: bool = False
    modality: str = "asserted"  # asserted | conditional | attributed | hypothetical
    attributed_to: str | None = None

    disjunctive: bool = False

    sdh_score: float = 0.0
    embedding: list[float] = field(default_factory=list)

    source_doc: str = ""
    sentence_id: int = 0
    raw_sentence: str = ""


@dataclass
class StructuralEvidence:
    """
    Persistent structural evidence (tables, lists) extracted during document ingestion.
    Indexed in ChromaDB alongside SVOA facts with 384-dimensional cosine embeddings.
    """

    id: str
    source_doc: str
    structure_type: str  # "table" | "list"
    content: str  # Rendered Markdown representation
    searchable_text: str  # Plain text used for semantic similarity search
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

