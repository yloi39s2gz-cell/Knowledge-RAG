import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class VectorStoreError(RuntimeError):
    pass


def ensure_collection(base_url: str, collection: str, vector_size: int) -> None:
    body = {
        "vectors": {
            "size": vector_size,
            "distance": "Cosine",
        }
    }
    _request("PUT", f"{base_url}/collections/{collection}", body)


def upsert_points(base_url: str, collection: str, points: list[dict[str, Any]]) -> None:
    _request("PUT", f"{base_url}/collections/{collection}/points?wait=true", {"points": points})


def search_points(
    base_url: str,
    collection: str,
    vector: list[float],
    limit: int,
) -> list[dict[str, Any]]:
    response = _request(
        "POST",
        f"{base_url}/collections/{collection}/points/search",
        {
            "vector": vector,
            "limit": limit,
            "with_payload": True,
        },
    )
    return response.get("result", [])


def _request(method: str, url: str, body: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    request = Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise VectorStoreError(f"Qdrant HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise VectorStoreError(f"Qdrant is unavailable: {exc.reason}") from exc
