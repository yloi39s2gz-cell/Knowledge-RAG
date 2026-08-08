from app.schemas.document import SearchResult
from app.services.rag import build_extractive_answer, evaluate_keywords, rewrite_query


def test_rewrite_query_expands_common_aliases() -> None:
    rewritten = rewrite_query("AI合规风险")
    assert "人工智能" in rewritten
    assert "合法合规" in rewritten


def test_keyword_evaluation_scores_expected_terms() -> None:
    assert evaluate_keywords("系统需要安全治理和合规审计", "安全,合规") == 1


def test_extractive_answer_contains_citation_marker() -> None:
    answer = build_extractive_answer(
        "人工智能安全",
        [
            SearchResult(
                document_id="doc-1",
                chunk_id="chunk-1",
                chunk_index=0,
                score=0.9,
                content="人工智能安全治理需要覆盖模型安全、数据安全和应用合规。",
                page_start=1,
                page_end=1,
            )
        ],
    )
    assert "[1]" in answer


if __name__ == "__main__":
    test_rewrite_query_expands_common_aliases()
    test_keyword_evaluation_scores_expected_terms()
    test_extractive_answer_contains_citation_marker()
