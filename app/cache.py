from typing import Optional
import redis.asyncio
from app.config import get_settings

_redis_client: Optional[redis.asyncio.Redis] = None


async def init_redis_client() -> redis.asyncio.Redis:
    global _redis_client
    settings = get_settings()
    _redis_client = redis.asyncio.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def get_redis_client() -> redis.asyncio.Redis:
    if _redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return _redis_client


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
