from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import app.db as db
from app.config import get_settings


@pytest.fixture(autouse=True)
def reset_db_pool():
    db._pool = None
    yield
    db._pool = None


def test_get_db_pool_uninitialized_raises():
    with pytest.raises(RuntimeError, match="Database pool is not initialized"):
        db.get_db_pool()


@pytest.mark.asyncio
async def test_init_db_pool():
    mock_pool = AsyncMock()
    with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
        mock_create_pool.return_value = mock_pool
        pool = await db.init_db_pool(min_size=5, max_size=20)
        settings = get_settings()
        mock_create_pool.assert_awaited_once_with(
            dsn=settings.database_url,
            min_size=5,
            max_size=20,
        )
        assert pool is mock_pool
        assert db.get_db_pool() is mock_pool


@pytest.mark.asyncio
async def test_close_db_pool():
    mock_pool = AsyncMock()
    db._pool = mock_pool

    await db.close_db_pool()

    mock_pool.close.assert_awaited_once()
    assert db._pool is None


@pytest.mark.asyncio
async def test_init_db_executes_ddl():
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    await db.init_db(mock_pool)
    assert mock_conn.execute.await_count == 2
    executed_statements = [call.args[0] for call in mock_conn.execute.await_args_list]
    assert any("CREATE TABLE IF NOT EXISTS trades" in stmt for stmt in executed_statements)
    assert any("CREATE INDEX IF NOT EXISTS idx_trades_ticker_time" in stmt for stmt in executed_statements)

    mock_conn.reset_mock()
    db._pool = mock_pool
    await db.init_db()
    assert mock_conn.execute.await_count == 2

