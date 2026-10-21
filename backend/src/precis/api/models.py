"""
Pydantic schemas for Précis API request and response bodies.
"""

from typing import Any

from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    client_id: str | None = Field(
        None,
        max_length=64,
        description="Random per-browser ID (client-<32 hex>) that keeps data stable across reloads",
    )


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT bearer access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token validity in seconds")


class IngestRequest(BaseModel):
    text: str = Field(
        ...,
        max_length=200_000,
        description="Document text to ingest",
    )
    document_name: str = Field(
        ...,
        max_length=255,
        description="Identifier/name for the document",
    )


class IngestResponse(BaseModel):
    document_name: str
    facts_extracted: int
    facts_stored: int
    latency_ms: int


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        max_length=4_000,
        description="Natural language question to answer",
    )
    session_id: str | None = Field(
        None,
        max_length=128,
        description="Optional session ID for conversational context tracking",
    )


class QueryResponse(BaseModel):
    answer: str
    facts_used: list[dict[str, Any]]
    tokens_used: int
    naive_rag_tokens: int
    compression_rate: float
    avg_sdh_score: float
    latency_ms: int
    model: str = ""
    inference_tokens: int = 0
    session_id: str | None = None
    # "conversation", "general" (model's own knowledge) or "document".
    answer_source: str = "document"


class HardwareResponse(BaseModel):
    cpu_cores: int
    cpu_model: str
    ram_gb: float
    has_gpu: bool
    gpu_name: str | None = None
    vram_gb: float | None = None
    recommended_model: str
    recommended_mode: str
    token_ceiling: int
    ml_accelerator: str | None = None


class StatsResponse(BaseModel):
    total_facts: int
    negated_count: int
    modality_breakdown: dict[str, int]
    avg_sdh_score: float


class DocumentInfo(BaseModel):
    name: str
    fact_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]


class FactListResponse(BaseModel):
    facts: list[dict[str, Any]]
    total: int
