import asyncio
import time
from collections import defaultdict

from redis.asyncio import Redis

from agent_yhzh.config import settings


class RateLimiter:
    def __init__(self) -> None:
        self._redis: Redis | None = None
        self._fallback: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def _redis_client(self) -> Redis | None:
        if self._redis is not None:
            return self._redis
        try:
            client = Redis.from_url(settings.redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
            return client
        except Exception:
            return None

    async def allow(self, key: str, limit: int | None = None) -> bool:
        limit = limit or settings.request_rate_limit_per_minute
        bucket = int(time.time() // 60)
        client = await self._redis_client()
        if client is not None:
            redis_key = f"agent-yhzh:rate:{key}:{bucket}"
            try:
                count = await client.incr(redis_key)
                if count == 1:
                    await client.expire(redis_key, 70)
                return count <= limit
            except Exception:
                self._redis = None

        now = time.monotonic()
        async with self._lock:
            history = [stamp for stamp in self._fallback[key] if now - stamp < 60]
            if len(history) >= limit:
                self._fallback[key] = history
                return False
            history.append(now)
            self._fallback[key] = history
            return True


rate_limiter = RateLimiter()
