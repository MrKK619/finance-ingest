from datetime import date, datetime, timezone
import json
from unittest.mock import AsyncMock, patch
import pytest
from app import cache
from app.cache import (
    close_redis_client,
    get_latest_tick,
    get_redis_client,
    init_redis_client,
    set_latest_tick,
)
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


@pytest.mark.asyncio
async def test_set_latest_tick_default_client_and_ttl():
    mock_client = AsyncMock()
    mock_client.set = AsyncMock(return_value=True)
    cache._redis_client = mock_client
    payload = {"price": "50000.00", "volume": 1.25}

    result = await set_latest_tick("btc-usd", payload)

    assert result is True
    mock_client.set.assert_awaited_once_with(
        "tick:BTC-USD",
        json.dumps(payload),
        ex=get_settings().REDIS_TTL_SECONDS,
    )


@pytest.mark.asyncio
async def test_set_latest_tick_custom_client_ttl_and_datetime_serialization():
    custom_client = AsyncMock()
    custom_client.set = AsyncMock(return_value=1)
    ts = datetime(2026, 11, 14, 7, 48, 47, tzinfo=timezone.utc)
    trade_date = date(2026, 11, 14)
    payload = {"price": "3200.50", "timestamp": ts, "trade_date": trade_date}

    result = await set_latest_tick("eth-usd", payload, client=custom_client, ttl_seconds=120)

    assert result is True
    custom_client.set.assert_awaited_once()
    call_args = custom_client.set.await_args
    assert call_args.args[0] == "tick:ETH-USD"
    assert json.loads(call_args.args[1]) == {
        "price": "3200.50",
        "timestamp": ts.isoformat(),
        "trade_date": trade_date.isoformat(),
    }
    assert call_args.kwargs == {"ex": 120}


@pytest.mark.asyncio
async def test_get_latest_tick_hit_default_client():
    mock_client = AsyncMock()
    expected = {"price": "50000.00", "ticker": "BTC-USD"}
    mock_client.get = AsyncMock(return_value=json.dumps(expected))
    cache._redis_client = mock_client

    result = await get_latest_tick("btc-usd")

    assert result == expected
    mock_client.get.assert_awaited_once_with("tick:BTC-USD")


@pytest.mark.asyncio
async def test_get_latest_tick_miss_custom_client():
    custom_client = AsyncMock()
    custom_client.get = AsyncMock(return_value=None)

    result = await get_latest_tick("sol-usd", client=custom_client)

    assert result is None
    custom_client.get.assert_awaited_once_with("tick:SOL-USD")
