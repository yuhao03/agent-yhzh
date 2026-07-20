import hashlib
import math

from agent_yhzh.config import settings
from agent_yhzh.services.model_config import RuntimeModelConfig, litellm_model_name


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


async def embed_text(
    content: str, runtime: RuntimeModelConfig | None = None
) -> list[float]:
    model = (runtime.embedding_model if runtime else settings.embedding_model) or settings.embedding_model
    api_key = runtime.api_key if runtime else settings.openai_api_key
    base_url = runtime.base_url if runtime else settings.model_base_url or None
    provider = runtime.provider if runtime else "openai"
    if model.startswith("local/") or (not api_key and not base_url):
        return deterministic_embedding(content)
    from litellm import aembedding

    response = await aembedding(
        model=litellm_model_name(provider, model),
        input=[content],
        api_key=api_key,
        api_base=base_url,
        timeout=runtime.timeout_seconds if runtime else 60,
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
