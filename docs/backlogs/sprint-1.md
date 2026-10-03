# Sprint 1 Backlog: Real-Time Market Ingestion & Caching Engine

## Sprint Details
* **Sprint Goal:** Establish the core project skeleton, containerized infrastructure, and the baseline asynchronous data ingestion pipeline from the live WebSocket feed to Redis and PostgreSQL.
* **Duration:** 1 to 2 weeks

---

## Sprint Backlog Items (Issues)

### 1. Project Scaffolding & Configuration Setup
* **Type:** Task / Infrastructure
* **Description:** Initialize the repository structure, define typed configuration settings, and set up local containerized infrastructure.
* **Acceptance Criteria:**
  * Directory layout (`app/`, `tests/`, `docs/backlogs/`) established matching production standards.
  * `docker-compose.yml` successfully spins up PostgreSQL 16 and Redis 7 on ports `5432` and `6379`.
  * `requirements.txt` includes pinned versions of FastAPI, Uvicorn, Pydantic, asyncpg, and redis-py.
  * `.gitignore` properly excludes virtual environments, caches, and local data volumes (`pgdata/`).

### 2. Database Schema & Connection Pool Implementation
* **Type:** Backend / Database
* **Description:** Implement asynchronous database connection pooling and automatic table creation with indexes for time-series queries.
* **Acceptance Criteria:**
  * `db.py` creates an `asyncpg` connection pool with bounded limits (`min_size=5`, `max_size=20`).
  * `init_db` script automatically provisions the `trades` table if it does not exist.
  * A B-tree compound index (`idx_trades_ticker_time`) is created on `(ticker, timestamp DESC)` to ensure fast range queries.
  * Implemented a batch-insertion helper function using `asyncpg` binary copy commands.

### 3. Redis Caching Client & TTL Management
* **Type:** Backend / Caching
* **Description:** Build an asynchronous Redis wrapper to handle ephemeral hot-state caching for incoming market ticks.
* **Acceptance Criteria:**
  * `cache.py` connects successfully to the local Redis instance using `redis.asyncio`.
  * `set_latest_tick()` writes JSON-serialized tick payloads with an enforced 60-second TTL to prevent stale data retention.
  * `get_latest_tick()` accurately retrieves and decodes the latest price snapshot for a given ticker.

### 4. Asynchronous WebSocket Ingestion Loop
* **Type:** Core Logic / Pipeline
* **Description:** Create a non-blocking background task that connects to the Coinbase WebSocket feed, parses raw payloads, and triggers cache updates and batched database writes.
* **Acceptance Criteria:**
  * `ingestor.py` connects to `wss://ws-feed.exchange.coinbase.com` and subscribes to target channels (e.g., `BTC-USD`, `ETH-USD`).
  * Incoming messages are validated using Pydantic schemas (`TradeTick`).
  * Valid ticks immediately update the Redis cache and append to a micro-batch buffer.
  * Buffer automatically flushes to PostgreSQL every 5 seconds or when it hits 50 records.

### 5. FastAPI REST Endpoints & Application Lifecycle
* **Type:** API / Backend
* **Description:** Expose public REST endpoints to query hot cache data and historical records, managed through FastAPI lifespan events.
* **Acceptance Criteria:**
  * `main.py` utilizes FastAPI `lifespan` context managers to cleanly initialize the database pool and spawn the background ingestion task on startup.
  * `GET /market/{ticker}/latest` queries Redis and returns the latest price snapshot (or `404` if missing).
  * `GET /market/{ticker}/history?limit=N` queries PostgreSQL and returns historical tick records sorted by timestamp descending.
  * Interactive Swagger documentation loads cleanly at `/docs`.