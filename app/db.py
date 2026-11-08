from datetime import datetime
from typing import Optional
import asyncpg
from app.config import get_settings

_pool: Optional[asyncpg.Pool] = None

CREATE_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(16) NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL
);
"""

CREATE_INDEX_DDL = """
CREATE INDEX IF NOT EXISTS idx_trades_ticker_time
ON trades (ticker, timestamp DESC);
"""


async def init_db_pool(min_size: int = 5, max_size: int = 20) -> asyncpg.Pool:
    global _pool
    settings = get_settings()
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=min_size,
        max_size=max_size,
    )
    return _pool


def get_db_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool


async def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def init_db(pool: Optional[asyncpg.Pool] = None) -> None:
    if pool is None:
        pool = get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_DDL)
        await conn.execute(CREATE_INDEX_DDL)


async def insert_trades_batch(
    records: list[tuple[str, float, float, datetime]],
    pool: Optional[asyncpg.Pool] = None,
) -> int:
    if len(records) == 0:
        return 0
    if pool is None:
        pool = get_db_pool()
    async with pool.acquire() as conn:
        await conn.copy_records_to_table(
            "trades",
            records=records,
            columns=["ticker", "price", "volume", "timestamp"],
        )
    return len(records)

