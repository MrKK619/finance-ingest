from unittest.mock import AsyncMock, MagicMock, patch
import asyncpg
from httpx import ASGITransport, AsyncClient
import pytest

import app.db as db
from app.main import app, lifespan


@pytest.fixture(autouse=True)
def reset_db_pool():
    db._pool = None
    yield
    db._pool = None


@pytest.mark.asyncio
async def test_health_db_success():
    """Verify that /health/db returns HTTP 200 with healthy status when DB is reachable."""
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = "SELECT 1"
    mock_conn.close.return_value = None

    with patch("app.main.asyncpg.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_conn

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health/db")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "database": "connected"}
        mock_connect.assert_awaited_once()
        mock_conn.execute.assert_awaited_once_with("SELECT 1")
        mock_conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_db_connection_oserror():
    """Verify that /health/db returns HTTP 503 with unhealthy status on OSError."""
    with patch(
        "app.main.asyncpg.connect",
        side_effect=OSError("Connection refused"),
    ) as mock_connect:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health/db")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert "Connection refused" in data["error"]
        mock_connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_db_postgres_error():
    """Verify that /health/db returns HTTP 503 with unhealthy status on PostgresError."""
    with patch(
        "app.main.asyncpg.connect",
        side_effect=asyncpg.PostgresError("Database connection failed"),
    ) as mock_connect:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health/db")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert "Database connection failed" in data["error"]
        mock_connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_db_query_failure():
    """Verify that /health/db cleans up connection and returns 503 if SELECT 1 fails."""
    mock_conn = AsyncMock()
    mock_conn.execute.side_effect = asyncpg.PostgresError("Query timeout")
    mock_conn.close.return_value = None

    with patch("app.main.asyncpg.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_conn

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health/db")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert "Query timeout" in data["error"]
        mock_conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_db_pool_success():
    """Verify that /health/db uses connection pool when pool is initialized."""
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = "SELECT 1"

    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    db._pool = mock_pool

    with patch("app.main.asyncpg.connect", new_callable=AsyncMock) as mock_connect:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health/db")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "database": "connected"}
        mock_pool.acquire.assert_called_once()
        mock_conn.execute.assert_awaited_once_with("SELECT 1")
        mock_connect.assert_not_called()


@pytest.mark.asyncio
async def test_health_db_pool_query_failure():
    """Verify that /health/db returns 503 when pool connection query fails."""
    mock_conn = AsyncMock()
    mock_conn.execute.side_effect = asyncpg.PostgresError("Pool connection timeout")

    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    db._pool = mock_pool

    with patch("app.main.asyncpg.connect", new_callable=AsyncMock) as mock_connect:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health/db")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert "Pool connection timeout" in data["error"]
        mock_pool.acquire.assert_called_once()
        mock_connect.assert_not_called()


@pytest.mark.asyncio
async def test_app_lifespan():
    """Verify that FastAPI lifespan initializes and closes the DB pool."""
    with patch("app.main.db.init_db_pool", new_callable=AsyncMock) as mock_init_pool, \
         patch("app.main.db.close_db_pool", new_callable=AsyncMock) as mock_close_pool:
        async with lifespan(app):
            mock_init_pool.assert_awaited_once()
            mock_close_pool.assert_not_awaited()
        mock_close_pool.assert_awaited_once()

