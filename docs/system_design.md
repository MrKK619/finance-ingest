# System Design Document: Real-Time Market Data Ingestion & Caching Engine

**Status:** In Development / Proposed
**Date:** October 2026
**Target Architecture:** Distributed Event-Driven Ingestion, Microservices, Time-Series Persistence

---

## 1. Executive Summary & Objective

The **Real-Time Market Data Ingestion & Caching Engine** is an event-driven backend service designed to consume, process, and persist high-frequency financial market trades with minimal end-to-end latency.

### Key Objectives:

- **Streaming Ingestion:** Maintain persistent WebSocket connections to public cryptocurrency/forex trade channels (e.g., Coinbase Pro WS) capable of processing 1,000+ ticks/minute.
- **Ultra-Low Latency Read Tier:** Provide sub-5ms lookups for the latest market prices and rolling metrics using an in-memory Redis caching layer.
- **Reliable Historical Persistence:** Batch-persist tick events to a relational/time-series PostgreSQL database with structured indexing to eliminate write bottlenecks.
- **RESTful API Interface:** Expose high-performance query endpoints via FastAPI for downstream analytics and quant dashboards.

---

## 2. High-Level Architecture Diagram

```
                 +--------------------------------------+
                 |   Coinbase Pro / Finnhub WebSocket   |
                 +--------------------------------------+
                                    |
                                    | (JSON tick events)
                                    v
                 +--------------------------------------+
                 |       Async Ingestion Worker         |
                 |      (Python asyncio / websockets)   |
                 +--------------------------------------+
                        |                       |
       (Single Hot Writes)             (Batch Flush: 5s / 50 ticks)
       (TTL = 60s)                              |
                        v                       v
             +--------------------+   +--------------------+
             |    Redis Cache     |   | PostgreSQL DB      |
             |   (In-Memory Tier) |   | (Time-Series Store)|
             +--------------------+   +--------------------+
                        ^                       ^
                        |                       |
            (Hot Price Lookups)      (Historical Range Queries)
                        |                       |
                 +--------------------------------------+
                 |          FastAPI Query Engine        |
                 |   (GET /latest, GET /history, /metrics)  |
                 +--------------------------------------+
                                    ^
                                    | (HTTP / JSON)
                                    v
                         [Downstream Clients / UI]
```

---

## 3. Component Breakdown

### 3.1. Ingestion Pipeline (`app/ingestor.py`)

- **Transport:** WebSocket client utilizing non-blocking asynchronous I/O (`websockets` library on Python `asyncio`).
- **Resilience & Backoff:** Implements automatic reconnection with exponential backoff on network disconnects or socket terminations.
- **Buffer Mechanism:** Collects incoming `TradeTick` objects in a memory-bounded queue. Writes are decoupled into:
  - **Direct Cache Sink:** Instant key-value updates to Redis.
  - **Batch Database Sink:** Flushed either when the buffer reaches 50 events or every 5.0 seconds, whichever occurs first.

### 3.2. In-Memory Caching Tier (`app/cache.py`)

- **Technology:** Redis 7 (Alpine container).
- **Key Strategy:**
  - `tick:{TICKER}`: Stores JSON payload of the latest trade `{price, volume, timestamp}` with a strict 60-second Time-To-Live (TTL) to prevent serving stale ticks.
  - `vwap:{TICKER}`: (Optional extension) Rolling 5-minute Volume Weighted Average Price cache.
- **Pattern:** Cache-aside for reads; direct cache update upon tick receipt.

### 3.3. Relational Time-Series Storage (`app/db.py`)

- **Technology:** PostgreSQL 16.
- **Schema Definition:**
  ```sql
  CREATE TABLE IF NOT EXISTS trades (
      id BIGSERIAL PRIMARY KEY,
      ticker VARCHAR(16) NOT NULL,
      price DOUBLE PRECISION NOT NULL,
      volume DOUBLE PRECISION NOT NULL,
      timestamp TIMESTAMPTZ NOT NULL
  );

  -- Composite B-Tree index for rapid time-bounded retrieval per asset
  CREATE INDEX IF NOT EXISTS idx_trades_ticker_time 
  ON trades (ticker, timestamp DESC);
  ```
- **Bulk Ingestion:** Employs `asyncpg.copy_records_to_table()` binary protocol to maximize throughput and bypass single-row `INSERT` overhead.

### 3.4. API Gateway & Query Engine (`app/main.py`)

- **Framework:** FastAPI with Uvicorn worker.
- **Endpoints:**
  - `GET /health`: Cluster health check (validates DB pool & Redis socket status).
  - `GET /market/{ticker}/latest`: Sub-5ms snapshot pulled directly from Redis.
  - `GET /market/{ticker}/history?limit=50`: Paginated time-series records from PostgreSQL.
  - `GET /market/{ticker}/vwap`: Calculates or reads 5-minute rolling metrics.

---

## 4. Data Models & Schemas

### Ingestion Contract (`TradeTick`)

```json
{
  "ticker": "BTC-USD",
  "price": 64250.50,
  "volume": 0.0421,
  "timestamp": "2026-10-02T12:40:00.123456Z"
}
```

### API Error Handling & Status Codes

- `200 OK`: Valid retrieval.
- `404 Not Found`: Ticker not found or cache entry expired (>60s staleness).
- `422 Unprocessable Entity`: Invalid request parameters or ticker format.
- `503 Service Unavailable`: Upstream database pool or Redis connection failure.

---

## 5. Non-Functional Requirements & Performance Targets

| Metric                               | Target                                           | Verification Method                  |
| :----------------------------------- | :----------------------------------------------- | :----------------------------------- |
| **Ingestion Latency**          | < 10ms from socket receipt to Redis cache write  | Log timestamp deltas                 |
| **Read Latency (`/latest`)** | < 5ms at 95th percentile (P95)                   | Load testing with Locust/K6          |
| **Throughput**                 | 1,500+ ticks/sec continuous without packet drops | Synthetic tick benchmark             |
| **Availability**               | Graceful reconnects under network partition      | Simulated SIGTERM / disconnect tests |
| **Memory Footprint**           | API + Ingestor < 150MB RSS                       | Docker container stats monitoring    |

---

## 6. Deployment & Container Orchestration

The application is containerized and reproducible using **Docker Compose**:

- `market_postgres`: Persists data to a named Docker volume (`pgdata`).
- `market_redis`: Ephemeral in-memory store with persistence disabled (pure LRU).
- `market_api`: Python application running FastAPI and background ingestion tasks.

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16-alpine
    container_name: market_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-market_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-market_password}
      POSTGRES_DB: ${POSTGRES_DB:-market_db}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: market_redis
    ports:
      - "6379:6379"

  api:
    build: .
    container_name: market_api
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://market_user:market_password@postgres:5432/market_db
      - REDIS_HOST=redis
      - REDIS_PORT=6379

volumes:
  pgdata:
```

---

## 7. Testing Strategy

1. **Unit Testing (`pytest`):**
   - Validation of `TradeTick` data casting and edge-case boundaries (negative prices, missing fields).
   - Redis serialization/deserialization logic.
2. **Integration Testing (`pytest-asyncio`, `testcontainers`):**
   - End-to-end socket parsing against mock WebSocket fixtures.
   - Batch database insertion verification and transactional rollback checks.
3. **Continuous Integration (CI):**
   - GitHub Actions workflow running `ruff` (linter/formatter) and `pytest` on every pull request.

---

## 8. Future Roadmap & Quant Extensions

- **Time-Series Engine Upgrade:** Migrate PostgreSQL table to **TimescaleDB hypertables** for automatic chunking and retention policies.
- **Order Book Level 2/3 Reconstruction:** Expand from trade tick ingestion to full order book depth snapshots with bid/ask spreads.
- **Low-Latency Core in C++ / Rust:** Port the ingestion and WebSocket decoding loop to C++20 or Rust, exposing bindings via PyO3 for ultra-low latency execution pipelines.
