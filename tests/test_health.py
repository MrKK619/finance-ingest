from unittest.mock import AsyncMock, patch
import asyncpg
from httpx import ASGITransport, AsyncClient
import pytest

from app.main import app


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

