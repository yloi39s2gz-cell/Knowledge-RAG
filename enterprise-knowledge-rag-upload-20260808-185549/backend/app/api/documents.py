from uuid import uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import require_api_key
from app.core.storage import save_upload_file
from app.db.session import get_db
from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentChunkRead, DocumentIndexResult, DocumentParseResult, DocumentRead
from app.services.document_parser import build_chunks, parse_document_pages
from app.services.embedding import embed_text
from app.services.vector_store import VectorStoreError, ensure_collection, upsert_points

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile,
    knowledge_base: str = Form(default="default"),
    _: None = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> Document:
    saved_file = await save_upload_file(
        file,
        upload_dir=settings.upload_dir,
        max_upload_mb=settings.max_upload_mb,
    )
    document = Document(
        id=saved_file.document_id,
        original_filename=saved_file.original_filename,
        stored_filename=saved_file.stored_filename,
        content_type=saved_file.content_type,
        size_bytes=saved_file.size_bytes,
        storage_path=saved_file.storage_path,
        knowledge_base=knowledge_base.strip() or "default",
        status="uploaded",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    statement = select(Document).order_by(Document.created_at.desc())
    return list(db.scalars(statement).all())


@router.post("/{document_id}/parse", response_model=DocumentParseResult)
def parse_document(
    document_id: str,
    _: None = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> DocumentParseResult:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    document.status = "parsing"
    db.commit()

    try:
        pages = parse_document_pages(document.storage_path)
        parsed_chunks = build_chunks(pages)
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        db.add_all(
            DocumentChunk(
                id=str(uuid4()),
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                char_count=chunk.char_count,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
            )
            for chunk in parsed_chunks
        )
        document.status = "parsed"
        db.commit()
    except ValueError as exc:
        document.status = "parse_failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return DocumentParseResult(
        document_id=document.id,
        status=document.status,
        chunk_count=len(parsed_chunks),
    )


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkRead])
def list_document_chunks(
    document_id: str,
    db: Session = Depends(get_db),
) -> list[DocumentChunk]:
    statement = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    return list(db.scalars(statement).all())


@router.post("/{document_id}/index", response_model=DocumentIndexResult)
def index_document(
    document_id: str,
    _: None = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> DocumentIndexResult:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    statement = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    chunks = list(db.scalars(statement).all())
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no chunks. Parse it before indexing.",
        )

    try:
        ensure_collection(
            settings.qdrant_url,
            settings.qdrant_collection,
            settings.embedding_dimension,
        )
        upsert_points(
            settings.qdrant_url,
            settings.qdrant_collection,
            [
                {
                    "id": chunk.id,
                    "vector": embed_text(chunk.content, settings.embedding_dimension),
                    "payload": {
                        "document_id": chunk.document_id,
                        "chunk_id": chunk.id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "page_start": chunk.page_start,
                        "page_end": chunk.page_end,
                        "source_filename": document.original_filename,
                        "knowledge_base": document.knowledge_base,
                    },
                }
                for chunk in chunks
            ],
        )
    except VectorStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    document.status = "indexed"
    db.commit()
    return DocumentIndexResult(
        document_id=document.id,
        status=document.status,
        indexed_count=len(chunks),
    )
