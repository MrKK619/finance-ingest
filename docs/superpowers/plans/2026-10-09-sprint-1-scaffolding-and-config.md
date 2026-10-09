# Sprint 1 Item 1: Scaffolding, Typed Configuration & Container Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish repository directory structure, strongly-typed application configuration with `pydantic-settings`, and containerized PostgreSQL 16 & Redis 7 services via Docker Compose with atomic commits.

**Architecture:** Application settings are encapsulated in a Pydantic v2 `BaseSettings` class with fail-fast validation and `.env` parsing. Backing data services (PostgreSQL and Redis) are orchestrated via Docker Compose with healthchecks and persistent named volumes, keeping the local developer runtime isolated and reproducible.

**Tech Stack:** Python 3.11+, Pydantic v2, `pydantic-settings`, Docker Compose, PostgreSQL 16 Alpine, Redis 7 Alpine, `pytest`.

---

## File Structure Map

```text
FinanceIngestor/
├── .env.example              # Documented environment variable template
├── .gitignore                # Environment exclusions, caches, container data
├── docker-compose.yml        # PostgreSQL 16 & Redis 7 container specifications
├── requirements.txt          # Pinned project dependencies
├── app/
│   ├── __init__.py           # Package marker
│   └── config.py             # Typed Settings model & singleton loader
└── tests/
    ├── __init__.py           # Test package marker
    └── test_config.py        # Configuration unit tests
```

---

### Task 1: Project Dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update `requirements.txt` with `pydantic-settings`**

Add `pydantic-settings>=2.2.0` to [requirements.txt](file:///c:/Users/kevin/Desktop/Coding/Projects/FinanceIngestor/requirements.txt):

```text
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
websockets>=12.0
redis>=5.0.0
asyncpg>=0.29.0
pydantic>=2.6.0
pydantic-settings>=2.2.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 2: Verify dependency installation**

Run:
```powershell
pip install -r requirements.txt
```
Expected output:
Successfully installed or satisfied `pydantic-settings`.

- [ ] **Step 3: User Git Commit**

Run in terminal:
```bash
git add requirements.txt
git commit -m "chore(deps): add pydantic-settings to project dependencies"
```

---

### Task 2: Container Infrastructure & Git Hygiene

**Files:**
- Modify: `.gitignore`
- Create: `docker-compose.yml`

- [ ] **Step 1: Update `.gitignore`**

Append project-specific exclusions to [.gitignore](file:///c:/Users/kevin/Desktop/Coding/Projects/FinanceIngestor/.gitignore):

```gitignore
# Environment & Secrets
.env
.env.local

# Local Data Volumes
pgdata/
redisdata/

# Testing & Cache
.pytest_cache/
__pycache__/
*.py[cod]
```

- [ ] **Step 2: Create `docker-compose.yml`**

Create [docker-compose.yml](file:///c:/Users/kevin/Desktop/Coding/Projects/FinanceIngestor/docker-compose.yml):

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: finance_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-market_data}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-market_data}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - finance-net

  redis:
    image: redis:7-alpine
    container_name: finance_redis
    restart: unless-stopped
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - finance-net

volumes:
  pgdata:
    driver: local
  redisdata:
    driver: local

networks:
  finance-net:
    driver: bridge
```

- [ ] **Step 3: Verify Docker Compose syntax**

Run:
```bash
docker compose config
```
Expected output: Valid resolved YAML without errors.

- [ ] **Step 4: User Git Commit**

Run in terminal:
```bash
git add docker-compose.yml .gitignore
git commit -m "feat(infra): add docker-compose configuration for postgres and redis"
```

---

### Task 3: Typed Configuration & Environment Template

**Files:**
- Create: `app/__init__.py`
- Create: `.env.example`
- Create: `app/config.py`

- [ ] **Step 1: Create package marker `app/__init__.py`**

Empty file or docstring package marker.

- [ ] **Step 2: Create `.env.example`**

Create [.env.example](file:///c:/Users/kevin/Desktop/Coding/Projects/FinanceIngestor/.env.example):

```env
# Application Settings
APP_NAME=FinanceIngestor
ENV=development
LOG_LEVEL=INFO

# PostgreSQL 16 Settings
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=market_data

# Redis 7 Settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Pipeline Configuration
BATCH_SIZE=50
BATCH_FLUSH_INTERVAL_SECONDS=5.0
REDIS_TTL_SECONDS=60
WEBSOCKET_FEED_URL=wss://ws-feed.exchange.coinbase.com
SUBSCRIBE_TICKERS=["BTC-USD", "ETH-USD"]
```

- [ ] **Step 3: Implement `app/config.py`**

Create [app/config.py](file:///c:/Users/kevin/Desktop/Coding/Projects/FinanceIngestor/app/config.py):

```python
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
```

- [ ] **Step 4: Verify module import and defaults**

Run:
```powershell
python -c "from app.config import get_settings; s = get_settings(); print('Config loaded successfully:', s.APP_NAME, s.database_url, s.redis_url)"
```
Expected output:
`Config loaded successfully: FinanceIngestor postgresql://postgres:postgres@localhost:5432/market_data redis://localhost:6379/0`

- [ ] **Step 5: User Git Commit**

Run in terminal:
```bash
git add app/__init__.py app/config.py .env.example
git commit -m "feat(config): implement typed application settings and env template"
```

---

### Task 4: Configuration Test Suite

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Create package marker `tests/__init__.py`**

Empty file or docstring package marker.

- [ ] **Step 2: Implement `tests/test_config.py`**

Create [tests/test_config.py](file:///c:/Users/kevin/Desktop/Coding/Projects/FinanceIngestor/tests/test_config.py):

```python
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
```

- [ ] **Step 3: Run the test suite**

Run:
```powershell
pytest tests/test_config.py -v
```
Expected output:
All 4 tests PASS with 100% success.

- [ ] **Step 4: User Git Commit**

Run in terminal:
```bash
git add tests/__init__.py tests/test_config.py
git commit -m "test(config): add unit tests for application settings validation"
```
