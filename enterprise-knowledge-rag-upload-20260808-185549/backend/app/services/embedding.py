import hashlib
import math
import re


def embed_text(text: str, dimension: int) -> list[float]:
    vector = [0.0] * dimension
    for token in _tokenize(text):
        digest = hashlib.md5(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text.lower())


if __name__ == "__main__":
    demo = embed_text("人工智能安全治理", 128)
    assert len(demo) == 128
    assert abs(math.sqrt(sum(value * value for value in demo)) - 1) < 1e-9
