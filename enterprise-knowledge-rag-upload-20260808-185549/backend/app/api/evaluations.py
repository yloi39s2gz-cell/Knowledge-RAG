from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_api_key
from app.db.session import get_db
from app.models.document import EvaluationCase, EvaluationRun
from app.schemas.document import EvaluationCaseCreate, EvaluationCaseRead, EvaluationRunRead
from app.services.llm_client import LLMError, generate_answer
from app.services.rag import build_extractive_answer, evaluate_keywords, rewrite_query
from app.api.search import _retrieve

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("/cases", response_model=EvaluationCaseRead, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: EvaluationCaseCreate,
    _: None = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> EvaluationCase:
    case = EvaluationCase(
        id=str(uuid4()),
        question=payload.question.strip(),
        expected_keywords=payload.expected_keywords.strip(),
    )
    if not case.question or not case.expected_keywords:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question and keywords are required")
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.get("/cases", response_model=list[EvaluationCaseRead])
def list_cases(db: Session = Depends(get_db)) -> list[EvaluationCase]:
    statement = select(EvaluationCase).order_by(EvaluationCase.created_at.desc())
    return list(db.scalars(statement).all())


@router.post("/cases/{case_id}/run", response_model=EvaluationRunRead)
def run_case(
    case_id: str,
    _: None = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> EvaluationRun:
    case = db.get(EvaluationCase, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation case not found")

    rewritten_query = rewrite_query(case.question)
    results = _retrieve(rewritten_query, 5, None)
    try:
        answer = generate_answer(case.question, results) or build_extractive_answer(case.question, results)
    except LLMError:
        answer = build_extractive_answer(case.question, results)
    score = evaluate_keywords(answer, case.expected_keywords)
    run = EvaluationRun(
        id=str(uuid4()),
        case_id=case.id,
        answer=answer,
        score=score,
        passed=score >= 0.6,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/runs", response_model=list[EvaluationRunRead])
def list_runs(db: Session = Depends(get_db)) -> list[EvaluationRun]:
    statement = select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(50)
    return list(db.scalars(statement).all())
