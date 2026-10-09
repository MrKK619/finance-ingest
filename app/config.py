from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Strongly-typed application settings using Pydantic v2 Settings.
    Reads defaults, with overrides sourced from environment variables or .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Metadata
    APP_NAME: str = Field(default="FinanceIngestor", description="Application service name")
    ENV: str = Field(default="development", description="Runtime environment: development, testing, production")
    LOG_LEVEL: str = Field(default="INFO", description="Standard logging level")

    # PostgreSQL Connection Settings
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL database username")
    POSTGRES_PASSWORD: str = Field(default="postgres", description="PostgreSQL database password")
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host address")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL network port")
    POSTGRES_DB: str = Field(default="market_data", description="PostgreSQL target database name")

    # Redis Connection Settings
    REDIS_HOST: str = Field(default="localhost", description="Redis host address")
    REDIS_PORT: int = Field(default=6379, description="Redis network port")
    REDIS_DB: int = Field(default=0, description="Redis logical database index")

    # Pipeline Tuning Settings
    BATCH_SIZE: int = Field(default=50, ge=1, description="Micro-batch size for database flushes")
    BATCH_FLUSH_INTERVAL_SECONDS: float = Field(default=5.0, gt=0, description="Maximum interval between flushes in seconds")
    REDIS_TTL_SECONDS: int = Field(default=60, gt=0, description="TTL in seconds for cached market ticks")
    WEBSOCKET_FEED_URL: str = Field(
        default="wss://ws-feed.exchange.coinbase.com",
        description="Target WebSocket endpoint for live tick ingestion",
    )
    SUBSCRIBE_TICKERS: List[str] = Field(
        default=["BTC-USD", "ETH-USD"],
        description="Currency pairs to subscribe to upon connection",
    )

    @property
    def database_url(self) -> str:
        """Returns standard PostgreSQL connection string."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def async_database_url(self) -> str:
        """Returns asyncpg-compatible PostgreSQL connection string."""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def redis_url(self) -> str:
        """Returns Redis connection string."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """Singleton getter for cached application settings."""
    return Settings()
