from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
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
    page_start: int | None
    page_end: int | None
