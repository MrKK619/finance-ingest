import asyncpg
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.APP_NAME)


async def check_db_connection() -> bool:
    """Verify connectivity to PostgreSQL database by executing SELECT 1."""
    current_settings = get_settings()
    conn = await asyncpg.connect(current_settings.database_url)
    try:
        await conn.execute("SELECT 1")
    finally:
        await conn.close()
    return True


@app.get("/health/db")
async def health_db():
    """Database health check endpoint returning 200 if reachable, 503 if unreachable."""
    try:
        await check_db_connection()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            },
        )

