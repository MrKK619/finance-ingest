import pytest
from pydantic import ValidationError
from app.config import Settings, get_settings


def test_default_settings():
    """Verify that settings initialize with expected defaults without environment variables."""
    settings = Settings()
    assert settings.APP_NAME == "FinanceIngestor"
    assert settings.ENV == "development"
    assert settings.POSTGRES_PORT == 5432
    assert settings.REDIS_PORT == 6379
    assert settings.BATCH_SIZE == 50
    assert settings.BATCH_FLUSH_INTERVAL_SECONDS == 5.0
    assert settings.REDIS_TTL_SECONDS == 60
    assert "BTC-USD" in settings.SUBSCRIBE_TICKERS
    assert settings.database_url == "postgresql://postgres:postgres@localhost:5432/market_data"
    assert settings.async_database_url == "postgresql+asyncpg://postgres:postgres@localhost:5432/market_data"
    assert settings.redis_url == "redis://localhost:6379/0"


def test_env_override(monkeypatch):
    """Verify that environment variables properly override default configuration values."""
    monkeypatch.setenv("APP_NAME", "MarketEngineTest")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("BATCH_SIZE", "100")
    monkeypatch.setenv("REDIS_HOST", "cache.internal")

    settings = Settings()
    assert settings.APP_NAME == "MarketEngineTest"
    assert settings.POSTGRES_PORT == 5433
    assert settings.BATCH_SIZE == 100
    assert settings.REDIS_HOST == "cache.internal"
    assert "cache.internal:6379" in settings.redis_url


def test_invalid_types_raise_validation_error():
    """Verify that invalid data types raise a Pydantic ValidationError on load."""
    with pytest.raises(ValidationError):
        Settings(POSTGRES_PORT="not-a-port")

    with pytest.raises(ValidationError):
        Settings(BATCH_SIZE=0)  # ge=1 invariant violated


def test_get_settings_caching():
    """Verify that get_settings provides a cached singleton instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
