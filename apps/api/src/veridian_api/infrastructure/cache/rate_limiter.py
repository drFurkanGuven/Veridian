import time
from typing import Optional

from veridian_api.core.config import Settings, get_settings
from veridian_api.infrastructure.cache.redis import get_redis_client


class RateLimiter:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()

    async def check(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        if limit <= 0:
            return True, 0

        redis = await get_redis_client()
        bucket = f"rate_limit:{key}"
        current = await redis.incr(bucket)
        if current == 1:
            await redis.expire(bucket, window_seconds)

        if current > limit:
            ttl = await redis.ttl(bucket)
            retry_after = ttl if ttl > 0 else window_seconds
            return False, retry_after

        return True, 0

    async def check_request(self, client_key: str) -> tuple[bool, int]:
        return await self.check(
            client_key,
            self._settings.rate_limit_requests_per_minute,
            window_seconds=60,
        )
