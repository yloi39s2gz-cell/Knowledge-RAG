import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings
from app.schemas.document import SearchResult


class LLMError(RuntimeError):
    pass


def generate_answer(query: str, results: list[SearchResult]) -> str | None:
    if not settings.deepseek_api_key:
        return None

    context = "\n\n".join(f"[{index}] {item.content}" for index, item in enumerate(results[:5], start=1))
    body = {
        "model": settings.deepseek_model,
        "messages": [
            {
                "role": "system",
                "content": "你是企业知识库问答助手。只能依据给定资料回答；每个关键结论后用[数字]标注引用；资料不足时直接说明不足。",
            },
            {"role": "user", "content": f"问题：{query}\n\n资料：\n{context}"},
        ],
        "temperature": 0.2,
    }
    request = Request(
        f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.deepseek_api_key}",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise LLMError(f"LLM HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise LLMError(f"LLM is unavailable: {exc.reason}") from exc

    return payload["choices"][0]["message"]["content"]
