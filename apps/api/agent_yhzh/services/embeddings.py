import hashlib
import math

from agent_yhzh.config import settings


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def deterministic_embedding(content: str) -> list[float]:
    """Dependency-free fallback suitable for local tests and lexical/vector fusion."""
    dimensions = settings.embedding_dimensions
    vector = [0.0] * dimensions
    normalized = " ".join(content.lower().split())
    tokens = normalized.split() or [normalized]
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        for offset in range(0, len(digest), 4):
            value = int.from_bytes(digest[offset : offset + 4], "big")
            index = value % dimensions
            vector[index] += -1.0 if value & 1 else 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


async def embed_text(content: str) -> list[float]:
    if settings.embedding_model.startswith("local/") or not settings.openai_api_key:
        return deterministic_embedding(content)
    from litellm import aembedding

    response = await aembedding(
        model=settings.embedding_model,
        input=[content],
        api_key=settings.openai_api_key,
    )
    return list(response.data[0]["embedding"])


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)
