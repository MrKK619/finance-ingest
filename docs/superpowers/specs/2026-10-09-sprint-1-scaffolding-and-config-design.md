# Technical Design Specification: Sprint 1 Item 1 — Scaffolding, Typed Configuration & Container Infrastructure

- **Date:** 2026-10-09
- **Project:** Real-Time Market Ingestion & Caching Engine (FinanceIngestor)
- **Author:** Antigravity & Engineering Pair
- **Sprint / Item:** Sprint 1, Item 1
- **Status:** Approved / Ready for Implementation

---

## 1. Context & Objectives

The goal of Sprint 1 Item 1 is to establish the production repository layout, implement compile-time type validation for environment configuration using `pydantic-settings`, and provision isolated local infrastructure (PostgreSQL 16 and Redis 7) using Docker Compose.

### Non-Functional Requirements
1. **12-Factor App Compliance:** Strict decoupling of code and configuration via environment variables and `.env` files.
2. **Fail-Fast Validation:** If any database or Redis connection variable is malformed (e.g. invalid port string), the application must fail on boot with explicit errors.
3. **Reproducible Environment:** Isolated data services running in Docker with volume persistence to prevent pollution of host OS.
4. **Clean Atomic Git History:** Changes implemented across small, verifiable, atomic commits following Conventional Commits.

---

## 2. Directory Structure

```text
FinanceIngestor/
├── .env.example              # Documented environment variable template (committed)
├── .gitignore                # Environment exclusions, caches, container data
├── docker-compose.yml        # PostgreSQL 16 & Redis 7 services
├── requirements.txt          # Pinned dependencies including pydantic-settings
├── app/
│   ├── __init__.py           # Package marker
│   └── config.py             # Strongly-typed configuration schema & loader
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-10-09-sprint-1-scaffolding-and-config-design.md
└── tests/
    ├── __init__.py           # Test package marker
    └── test_config.py        # Settings unit tests (defaults & env overrides)
```

---

## 3. Configuration Architecture (`app/config.py` & `.env.example`)

### 3.1 Pydantic Settings Specification
We define a `Settings` class inheriting from `pydantic_settings.BaseSettings`:

* **Application Settings:**
  * `APP_NAME`: `str = "FinanceIngestor"`
  * `ENV`: `str = "development"`
  * `LOG_LEVEL`: `str = "INFO"`
* **PostgreSQL Settings:**
  * `POSTGRES_USER`: `str = "postgres"`
  * `POSTGRES_PASSWORD`: `str = "postgres"`
  * `POSTGRES_HOST`: `str = "localhost"`
  * `POSTGRES_PORT`: `int = 5432`
  * `POSTGRES_DB`: `str = "market_data"`
  * `database_url` (property): `postgresql://{user}:{password}@{host}:{port}/{db}`
  * `async_database_url` (property): `postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}`
* **Redis Settings:**
  * `REDIS_HOST`: `str = "localhost"`
  * `REDIS_PORT`: `int = 6379`
  * `REDIS_DB`: `int = 0`
  * `redis_url` (property): `redis://{host}:{port}/{db}`
* **Pipeline Tunables:**
  * `BATCH_SIZE`: `int = 50`
  * `BATCH_FLUSH_INTERVAL_SECONDS`: `float = 5.0`
  * `REDIS_TTL_SECONDS`: `int = 60`
  * `WEBSOCKET_FEED_URL`: `str = "wss://ws-feed.exchange.coinbase.com"`
  * `SUBSCRIBE_TICKERS`: `list[str] = ["BTC-USD", "ETH-USD"]`

`SettingsConfigDict` will be configured with:
* `env_file = ".env"`
* `env_file_encoding = "utf-8"`
* `case_sensitive = False`
* `extra = "ignore"`

### 3.2 Singleton Provider
To avoid repeated environment reading and file parsing, `get_settings()` is decorated with `@functools.lru_cache`:
```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## 4. Container Infrastructure (`docker-compose.yml`)

### 4.1 PostgreSQL Service
* **Image:** `postgres:16-alpine`
* **Port Mapping:** `5432:5432`
* **Environment:** `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`, `POSTGRES_DB=market_data`
* **Volumes:** `pgdata:/var/lib/postgresql/data`
* **Healthcheck:** `pg_isready -U postgres -d market_data`

### 4.2 Redis Service
* **Image:** `redis:7-alpine`
* **Port Mapping:** `6379:6379`
* **Volumes:** `redisdata:/data`
* **Healthcheck:** `redis-cli ping`

### 4.3 Volumes & Network
* Named volumes: `pgdata`, `redisdata`
* Bridge network: `finance-net`

---

## 5. Verification & Testing Strategy

1. **Unit Testing (`tests/test_config.py`):**
   * `test_default_settings`: Verifies factory defaults load expected URLs and intervals.
   * `test_env_override`: Sets temporary environment variables (`monkeypatch`) and verifies `Settings` accurately parses and overrides defaults.
   * `test_invalid_types_raise_validation_error`: Validates that invalid numeric formats (e.g. `POSTGRES_PORT="invalid"`) raise `pydantic.ValidationError`.
2. **Compose Validation:**
   * Run `docker compose config` to verify YAML schema correctness and volume definitions.

---

## 6. Atomic Commit Plan

To ensure human-like git hygiene, the implementation will be delivered across 4 atomic commits:

1. **Commit 1 (Dependencies):**
   * Message: `chore(deps): add pydantic-settings to project dependencies`
   * Target: `requirements.txt`
2. **Commit 2 (Infrastructure):**
   * Message: `feat(infra): add docker-compose configuration for postgres and redis`
   * Target: `docker-compose.yml`, `.gitignore`
3. **Commit 3 (Configuration):**
   * Message: `feat(config): implement typed application settings and env template`
   * Target: `app/__init__.py`, `app/config.py`, `.env.example`
4. **Commit 4 (Tests):**
   * Message: `test(config): add unit tests for application settings validation`
   * Target: `tests/__init__.py`, `tests/test_config.py`
