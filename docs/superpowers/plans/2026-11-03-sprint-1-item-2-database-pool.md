# Sprint 1 Item 2: Database Schema & Connection Pool Implementation Plan

> **For agentic workers:** Follow `/cavecrew` guidelines strictly. All subagent outputs must adhere to `/caveman` constraints. Changes must be verified via sandbox tests before diff review. Commits remain manual under user execution.

**Goal:** Implement asynchronous PostgreSQL connection pooling, automated schema provisioning (`trades` table and compound index), and high-throughput batch insertion using `asyncpg.copy_records_to_table()` in `app/db.py` with comprehensive unit and integration tests in `tests/test_db.py`.

**Architecture:** 
- `asyncpg.Pool` acts as a managed singleton pool across FastAPI lifespan and background ingestion workers (`min_size=5`, `max_size=20`).
- DDL initialization creates the relational time-series schema idempotently (`IF NOT EXISTS`).
- Bulk ingestion leverages the PostgreSQL binary COPY protocol to bypass per-row statement overhead and achieve sub-millisecond multi-record ingestion.

**Tech Stack:** Python 3.12, `asyncpg>=0.29.0`, PostgreSQL 16, `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`.

---

## Proposed Changes

### File Structure Map
```text
FinanceIngestor/
├── app/
│   ├── config.py             # Existing typed settings
│   ├── main.py               # FastAPI app & health check
│   └── db.py                 # [NEW] Connection pool, DDL schema, & batch ingestion
└── tests/
    ├── test_config.py        # Existing configuration tests
    ├── test_health.py        # Existing health check tests
    └── test_db.py            # [NEW] Unit & mock verification for DB operations
```

---

## Detailed Task Breakdown

### Task 1: Database Module (`app/db.py`)

**Files:**
- Create: `app/db.py`

- [ ] **Step 1: Implement Pool Management**
  - Global variable `_pool: Optional[asyncpg.Pool] = None`.
  - `init_db_pool(min_size: int = 5, max_size: int = 20) -> asyncpg.Pool`:
    - Reads connection string from `app.config.get_settings().database_url`.
    - Initializes `asyncpg.create_pool(...)` and stores reference in `_pool`.
  - `get_db_pool() -> asyncpg.Pool`:
    - Returns `_pool`.
    - Raises `RuntimeError("Database pool is not initialized")` if `_pool is None`.
  - `close_db_pool() -> None`:
    - Calls `await _pool.close()` if active.
    - Resets `_pool = None`.

- [ ] **Step 2: Implement Automated Schema Provisioning (`init_db`)**
  - `init_db(pool: Optional[asyncpg.Pool] = None) -> None`:
    - Defaults to `get_db_pool()`.
    - Executes DDL idempotently:
      ```sql
      CREATE TABLE IF NOT EXISTS trades (
          id BIGSERIAL PRIMARY KEY,
          ticker VARCHAR(16) NOT NULL,
          price DOUBLE PRECISION NOT NULL,
          volume DOUBLE PRECISION NOT NULL,
          timestamp TIMESTAMPTZ NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_trades_ticker_time
      ON trades (ticker, timestamp DESC);
      ```

- [ ] **Step 3: Implement High-Throughput Batch Ingestion**
  - `insert_trades_batch(records: list[tuple[str, float, float, datetime]], pool: Optional[asyncpg.Pool] = None) -> int`:
    - Defaults to `get_db_pool()`.
    - Early exit if `len(records) == 0` (returns `0`).
    - Acquires connection from pool: `async with pool.acquire() as conn:`.
    - Executes binary copy:
      ```python
      await conn.copy_records_to_table(
          "trades",
          records=records,
          columns=["ticker", "price", "volume", "timestamp"],
      )
      ```
    - Returns `len(records)`.

---

### Task 2: Unit Test Suite (`tests/test_db.py`)

**Files:**
- Create: `tests/test_db.py`

- [ ] **Step 1: Test Pool Lifecycle & Invariants**
  - `test_get_db_pool_uninitialized_raises()`:
    - Asserts calling `get_db_pool()` when `_pool is None` raises `RuntimeError`.
  - `test_init_db_pool()`:
    - Mocks `asyncpg.create_pool` with `AsyncMock`.
    - Asserts pool created with `min_size=5`, `max_size=20`, and `get_db_pool()` returns mocked instance.
  - `test_close_db_pool()`:
    - Mocks active pool and verifies `close()` awaited and `_pool` reset to `None`.

- [ ] **Step 2: Test Schema Provisioning**
  - `test_init_db_executes_ddl()`:
    - Mocks connection and pool.
    - Verifies `init_db()` executes table and compound index creation queries.

- [ ] **Step 3: Test Batch Ingestion**
  - `test_insert_trades_batch_success()`:
    - Mocks `conn.copy_records_to_table`.
    - Passes sample trade tuples `[("BTC-USD", 65000.5, 0.25, datetime.now(timezone.utc))]`.
    - Asserts `copy_records_to_table` called with table name `"trades"` and correct columns.
    - Verifies returned count equals record count.
  - `test_insert_trades_batch_empty()`:
    - Passes empty list `[]`.
    - Asserts returns `0` without attempting to acquire connection.

---

### Task 3: Integration with Health Endpoint

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Refactor `check_db_connection()` to utilize pool if initialized**
  - If `_pool` exists, execute `SELECT 1` via `pool.acquire()`.
  - Fall back gracefully to single ad-hoc connection if pool uninitialized (preserves standalone `/health/db` tests).

---

## Verification Plan

### Automated Unit Testing
Run test suite outside sandbox (due to Windows socket permission constraints with pytest-asyncio):
```powershell
.\venv\Scripts\pytest tests/test_db.py tests/test_health.py tests/test_config.py -v
```

**Success Criteria:**
- 100% tests passing across all three test modules.
- Bounded connection pool limits respected.
- Schema creation statements idempotent.
- Zero open connection leaks.

---

## User Manual Commit Instructions
After automated verification (`TESTS: PASS`) and diff review (`REVIEW: PASS`):
```bash
git add app/db.py app/main.py tests/test_db.py docs/superpowers/plans/2026-11-03-sprint-1-item-2-database-pool.md
git commit -m "feat(db): implement asyncpg connection pool, schema provisioning, and batch insertion"
```

