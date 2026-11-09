# Sprint 1 Item 3: Redis Caching Client & TTL Management Implementation Plan

> **For agentic workers:** Follow `/cavecrew` guidelines strictly. All subagent outputs must adhere to `/caveman` constraints. Changes must be verified via sandbox tests before diff review. Commits remain manual under user execution.

**Goal:** Implement an asynchronous Redis caching wrapper in `app/cache.py` with singleton client lifecycle management, key-value storage of market tick payloads with strict 60-second TTLs, JSON serialization/deserialization, and comprehensive unit tests in `tests/test_cache.py`. Integrate Redis lifecycle and health checking into `app/main.py`.

**Architecture:**
- Uses `redis.asyncio` (already in `requirements.txt`) with connection URL from `app.config.get_settings().redis_url`.
- Singleton pattern mirroring `app/db.py`: `init_redis_client()`, `get_redis_client()`, and `close_redis_client()`.
- Hot-tier key scheme: `tick:{ticker}` storing JSON-encoded `{price, volume, timestamp}`.
- Enforced TTL: `REDIS_TTL_SECONDS` (default: 60s from `Settings`) to prevent serving stale ticks during market pauses or feed outages.
- Non-blocking read/write API: `set_latest_tick()` and `get_latest_tick()`.

**Tech Stack:** Python 3.12, `redis.asyncio>=5.0.0`, Redis 7, `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`.

---

## File Structure Map

```text
FinanceIngestor/
├── app/
│   ├── config.py             # Existing typed settings (REDIS_HOST, REDIS_PORT, REDIS_TTL_SECONDS, redis_url)
│   ├── db.py                 # Existing database connection pool & batch copy
│   ├── cache.py              # [NEW] Redis client lifecycle, set_latest_tick, get_latest_tick
│   └── main.py               # Updated FastAPI lifespan & /health/redis endpoint
└── tests/
    ├── conftest.py           # Existing sandbox asyncio fix
    ├── test_config.py        # Configuration tests
    ├── test_db.py            # Database pool tests
    ├── test_health.py        # Health & lifespan tests
    └── test_cache.py         # [NEW] Redis caching unit tests
```

---

## Atomic Iteration Breakdown

To continue our atomic commit workflow, Item 3 will be developed in **3 small iterations**:

### Iteration 1: Redis Client Lifecycle (`app/cache.py`) & Tests
- Global client singleton `_redis_client: Optional[redis.asyncio.Redis] = None`.
- `init_redis_client() -> redis.asyncio.Redis`:
  - Connects using `get_settings().redis_url` with `decode_responses=True`.
- `get_redis_client() -> redis.asyncio.Redis`:
  - Returns `_redis_client`.
  - Raises `RuntimeError("Redis client is not initialized")` if uninitialized.
- `close_redis_client() -> None`:
  - Awaits `_redis_client.aclose()`, sets `_redis_client = None`.
- `tests/test_cache.py`:
  - Unit tests for initialization, uninitialized error guard, and graceful shutdown.
- **Commit**: `feat(cache): implement async redis client lifecycle management`

### Iteration 2: Tick Cache Operations with TTL (`set_latest_tick`, `get_latest_tick`) & Tests
- `set_latest_tick(ticker: str, payload: dict, client: Optional[Redis] = None, ttl_seconds: Optional[int] = None) -> bool`:
  - Normalizes ticker to uppercase.
  - Serializes `payload` to JSON string (supporting ISO formatted datetime/timestamps).
  - Key format: `tick:{ticker}`.
  - Stores via `await client.set(key, serialized_payload, ex=ttl_seconds or settings.REDIS_TTL_SECONDS)`.
- `get_latest_tick(ticker: str, client: Optional[Redis] = None) -> Optional[dict]`:
  - Retrieves raw string via `await client.get(f"tick:{ticker.upper()}")`.
  - Deserializes JSON and returns `dict` (or `None` if key expired / not found).
- `tests/test_cache.py`:
  - Unit tests verifying key formatting, JSON serialization, TTL parameter propagation, retrieval of valid ticks, and cache misses returning `None`.
- **Commit**: `feat(cache): implement set_latest_tick and get_latest_tick with enforced TTL`

### Iteration 3: FastAPI Lifespan & `/health/redis` Endpoint Integration
- Update `app/main.py`:
  - Wire `init_redis_client()` and `close_redis_client()` into FastAPI `lifespan`.
  - Add `check_redis_connection() -> bool` using `client.ping()`.
  - Add `GET /health/redis`:
    - Returns `200 OK` `{"status": "healthy", "redis": "connected"}` if ping succeeds.
    - Returns `503 Service Unavailable` with `error` details on connection failure.
- Update `tests/test_health.py`:
  - Tests covering `/health/redis` (success, connection error, ping timeout).
- **Commit**: `feat(api): integrate redis client with application lifespan and health check`

---

## Verification Plan

### Automated Unit Testing
Run full test suite in sandbox:
```powershell
.\venv\Scripts\pytest tests/test_cache.py tests/test_health.py tests/test_db.py tests/test_config.py -v
```

**Success Criteria:**
- 100% tests passing inside sandbox.
- Ticker keys strictly formatted as `tick:{TICKER}`.
- 60-second TTL enforced on all tick writes.
- Graceful `None` on expired or absent cache hits.
- Zero client connection leaks on shutdown.

