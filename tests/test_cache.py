from unittest.mock import AsyncMock, patch
import pytest
from app import cache
from app.cache import close_redis_client, get_redis_client, init_redis_client
from app.config import get_settings


@pytest.fixture(autouse=True)
def reset_redis_client():
    cache._redis_client = None
    yield
    cache._redis_client = None


def test_get_redis_client_uninitialized_raises():
    with pytest.raises(RuntimeError, match="Redis client is not initialized"):
        get_redis_client()


@pytest.mark.asyncio
async def test_init_redis_client():
    mock_redis = AsyncMock()
    with patch("redis.asyncio.from_url", return_value=mock_redis) as mock_from_url:
        client = await init_redis_client()
        settings = get_settings()
        mock_from_url.assert_called_once_with(settings.redis_url, decode_responses=True)
        assert client == mock_redis
        assert get_redis_client() == mock_redis


@pytest.mark.asyncio
async def test_close_redis_client():
    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()
    cache._redis_client = mock_client

    await close_redis_client()

    mock_client.aclose.assert_awaited_once()
    assert cache._redis_client is None
