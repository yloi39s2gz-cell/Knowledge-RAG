from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    knowledge_base: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkRead(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    char_count: int
    page_start: int | None
    page_end: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentParseResult(BaseModel):
    document_id: str
    status: str
    chunk_count: int


class DocumentIndexResult(BaseModel):
    document_id: str
    status: str
    indexed_count: int


class SearchResult(BaseModel):
    document_id: str
    chunk_id: str
    chunk_index: int
    score: float
    content: str
    source_filename: str | None = None
    page_start: int | None
    page_end: int | None
    keyword_score: float = 0
    combined_score: float = 0


class Citation(BaseModel):
    index: int
    document_id: str
    chunk_id: str
    source_filename: str | None = None
    page_start: int | None
    page_end: int | None
    content: str


class QAResponse(BaseModel):
    query: str
    rewritten_query: str
    answer: str
    citations: list[Citation]
    latency_ms: float


class SearchLogRead(BaseModel):
    id: str
    query: str
    rewritten_query: str
    answer: str
    hit_count: int
    latency_ms: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationCaseCreate(BaseModel):
    question: str
    expected_keywords: str


class EvaluationCaseRead(BaseModel):
    id: str
    question: str
    expected_keywords: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationRunRead(BaseModel):
    id: str
    case_id: str
    answer: str
    score: float
    passed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
