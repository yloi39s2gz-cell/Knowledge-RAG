from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.document import SearchLog
from app.schemas.document import QAResponse, SearchLogRead, SearchResult
from app.services.embedding import embed_text
from app.services.llm_client import LLMError, generate_answer
from app.services.rag import build_citations, build_extractive_answer, rerank_results, rewrite_query
from app.services.vector_store import VectorStoreError, search_points

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
def search_knowledge(
    query: str = Query(min_length=1),
    limit: int = Query(default=5, ge=1, le=20),
    knowledge_base: str | None = Query(default=None),
) -> list[SearchResult]:
    return _retrieve(query, limit, knowledge_base)


@router.get("/answer", response_model=QAResponse)
def answer_question(
    query: str = Query(min_length=1),
    limit: int = Query(default=5, ge=1, le=10),
    knowledge_base: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> QAResponse:
    start = perf_counter()
    rewritten_query = rewrite_query(query)
    results = _retrieve(rewritten_query, limit, knowledge_base)
    try:
        answer = generate_answer(query, results) or build_extractive_answer(query, results)
    except LLMError:
        answer = build_extractive_answer(query, results)

    latency_ms = round((perf_counter() - start) * 1000, 2)
    db.add(
        SearchLog(
            id=str(uuid4()),
            query=query,
            rewritten_query=rewritten_query,
            answer=answer,
            hit_count=len(results),
            latency_ms=latency_ms,
        )
    )
    db.commit()
    return QAResponse(
        query=query,
        rewritten_query=rewritten_query,
        answer=answer,
        citations=build_citations(results),
        latency_ms=latency_ms,
    )


@router.get("/logs", response_model=list[SearchLogRead])
def list_search_logs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[SearchLog]:
    statement = select(SearchLog).order_by(SearchLog.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


def _retrieve(query: str, limit: int, knowledge_base: str | None) -> list[SearchResult]:
    try:
        points = search_points(
            settings.qdrant_url,
            settings.qdrant_collection,
            embed_text(query, settings.embedding_dimension),
            limit * 4,
            knowledge_base,
        )
    except VectorStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return rerank_results(query, points, limit)
