from datetime import date, datetime
import json
from typing import Any, Optional
import redis.asyncio
from app.config import get_settings

_redis_client: Optional[redis.asyncio.Redis] = None


def _tick_key(ticker: str) -> str:
    return f"tick:{ticker.upper()}"


def _json_default(obj: Any) -> str:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


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


async def set_latest_tick(
    ticker: str,
    payload: dict[str, Any],
    client: Optional[redis.asyncio.Redis] = None,
    ttl_seconds: Optional[int] = None,
) -> bool:
    """Cache the latest tick payload for a ticker with an optional TTL."""
    redis_client = get_redis_client() if client is None else client
    ttl = get_settings().REDIS_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    serialized = json.dumps(payload, default=_json_default)
    result = await redis_client.set(_tick_key(ticker), serialized, ex=ttl)
    return bool(result)


async def get_latest_tick(
    ticker: str,
    client: Optional[redis.asyncio.Redis] = None,
) -> Optional[dict[str, Any]]:
    """Fetch and deserialize the latest cached tick payload for a ticker."""
    redis_client = get_redis_client() if client is None else client
    raw = await redis_client.get(_tick_key(ticker))
    if raw is None:
        return None
    return json.loads(raw)
