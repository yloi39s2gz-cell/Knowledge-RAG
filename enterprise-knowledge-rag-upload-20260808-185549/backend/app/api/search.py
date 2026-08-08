from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import settings
from app.schemas.document import SearchResult
from app.services.embedding import embed_text
from app.services.vector_store import VectorStoreError, search_points

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
def search_knowledge(
    query: str = Query(min_length=1),
    limit: int = Query(default=5, ge=1, le=20),
) -> list[SearchResult]:
    try:
        points = search_points(
            settings.qdrant_url,
            settings.qdrant_collection,
            embed_text(query, settings.embedding_dimension),
            limit,
        )
    except VectorStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    results: list[SearchResult] = []
    for point in points:
        payload = point.get("payload") or {}
        results.append(
            SearchResult(
                document_id=payload.get("document_id", ""),
                chunk_id=payload.get("chunk_id", ""),
                chunk_index=payload.get("chunk_index", 0),
                score=point.get("score", 0.0),
                content=payload.get("content", ""),
                page_start=payload.get("page_start"),
                page_end=payload.get("page_end"),
            )
        )
    return results
