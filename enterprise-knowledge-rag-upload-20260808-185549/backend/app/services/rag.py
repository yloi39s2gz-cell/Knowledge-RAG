import re
from typing import Any

from app.schemas.document import Citation, SearchResult


def rewrite_query(query: str) -> str:
    normalized = re.sub(r"\s+", " ", query).strip()
    aliases = {
        "AI": "人工智能",
        "ai": "人工智能",
        "风控": "风险控制",
        "合规": "合法合规",
        "隐私": "个人信息 数据安全",
        "幻觉": "不准确 不可信",
    }
    expanded = [normalized]
    for source, target in aliases.items():
        if source in normalized and target not in normalized:
            expanded.append(target)
    return " ".join(expanded)


def rerank_results(query: str, points: list[dict[str, Any]], limit: int) -> list[SearchResult]:
    query_tokens = set(_tokens(query))
    results: list[SearchResult] = []
    for point in points:
        payload = point.get("payload") or {}
        content = payload.get("content", "")
        keyword_score = _keyword_score(query_tokens, content)
        vector_score = float(point.get("score", 0.0))
        combined_score = vector_score * 0.7 + keyword_score * 0.3
        results.append(
            SearchResult(
                document_id=payload.get("document_id", ""),
                chunk_id=payload.get("chunk_id", ""),
                chunk_index=payload.get("chunk_index", 0),
                score=vector_score,
                content=content,
                source_filename=payload.get("source_filename"),
                page_start=payload.get("page_start"),
                page_end=payload.get("page_end"),
                keyword_score=keyword_score,
                combined_score=combined_score,
            )
        )
    results.sort(key=lambda item: item.combined_score, reverse=True)
    return results[:limit]


def build_extractive_answer(query: str, results: list[SearchResult]) -> str:
    if not results:
        return "没有在知识库中检索到足够相关的内容，请补充文档或换一种问法。"

    lines = ["根据当前知识库，结论如下："]
    for index, result in enumerate(results[:3], start=1):
        lines.append(f"{index}. {_compact(result.content)} [{index}]")
    lines.append("以上回答仅基于检索到的文档片段，建议结合引用来源核对原文。")
    return "\n".join(lines)


def build_citations(results: list[SearchResult]) -> list[Citation]:
    return [
        Citation(
            index=index,
            document_id=result.document_id,
            chunk_id=result.chunk_id,
            source_filename=result.source_filename,
            page_start=result.page_start,
            page_end=result.page_end,
            content=result.content,
        )
        for index, result in enumerate(results, start=1)
    ]


def evaluate_keywords(answer: str, expected_keywords: str) -> float:
    keywords = [keyword.strip() for keyword in re.split(r"[,，、\s]+", expected_keywords) if keyword.strip()]
    if not keywords:
        return 0.0
    matched = sum(1 for keyword in keywords if keyword in answer)
    return matched / len(keywords)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}|[\u4e00-\u9fff]", text.lower())


def _keyword_score(query_tokens: set[str], content: str) -> float:
    if not query_tokens:
        return 0.0
    content_tokens = set(_tokens(content))
    return len(query_tokens & content_tokens) / len(query_tokens)


def _compact(text: str, max_chars: int = 220) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


if __name__ == "__main__":
    rewritten = rewrite_query("AI隐私风险有哪些？")
    assert "人工智能" in rewritten
    assert evaluate_keywords("安全 合规 风险", "安全,风险") == 1
