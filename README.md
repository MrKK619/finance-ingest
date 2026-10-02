# Real-Time Market Ingestion & Caching Engine

[![CI](https://github.com/your-username/market-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/market-engine/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An asynchronous, event-driven market data pipeline built in Python. The system consumes live WebSocket trade streams, maintains a sub-millisecond in-memory cache in Redis, and persists batched transaction records into PostgreSQL with optimized B-tree indexing for low-latency time-series queries.

---

## Architecture Overview

                      ┌───────────────────────────┐
                      │   Coinbase WebSocket Feed │
                      │      (WSS Streaming)      │
                      └─────────────┬─────────────┘
                                    │
                                    │ Raw JSON Ticks
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FastAPI Application (Asynchronous Event Loop)                               │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ Asynchronous Ingestor (websockets / asyncio)                        │   │
│   │  • Parses payload into validated Pydantic models (TradeTick)        │   │
│   │  • Dispatches updates concurrently via non-blocking I/O             │   │
│   └───────────────┬─────────────────────────────────────┬───────────────┘   │
│                   │                                     │                   │
│                   ▼ (Immediate TTL Cache)               ▼ (Buffered Batch)  │
│        ┌─────────────────────┐               ┌─────────────────────┐        │
│        │  MarketCache Client │               │ Micro-Batch Buffer  │        │
│        └──────────┬──────────┘               └──────────┬──────────┘        │
└───────────────────┼─────────────────────────────────────┼───────────────────┘
│                                     │
▼                                     ▼ COPY / bulk insert
┌─────────────────────┐               ┌─────────────────────┐
│     Redis 7.0       │               │    PostgreSQL 16    │
│  (Latest Tick Cache)│               │  (Historical Store) │
└──────────┬──────────┘               └──────────┬──────────┘
│                                     │
│ Sub-5ms Read                        │ Indexed Range
└───────────────┐     ┌───────────────┘
▼     ▼
┌───────────────────────────┐
│    FastAPI REST Server    │
│   /market/{ticker}/latest │
│  /market/{ticker}/history │
└───────────────────────────┘


### Key Design Trade-Offs

* **Cache-Aside & Immediate Ephemeral Reads:** Incoming ticks update Redis with a 60-second TTL. This decouples fast client reads (`GET /latest`) from database disk operations and shields the relational store from traffic spikes.
* **Micro-Batch Database Writes:** Direct inserts per tick under high network load cause row lock contention. The ingestor buffers incoming records and uses `asyncpg` binary bulk operations (`copy_records_to_table`) every 5 seconds or 50 items, drastically reducing transaction overhead.
* **Connection Pooling:** PostgreSQL operations are executed through an `asyncpg` connection pool with bounded size limits (`min_size=5`, `max_size=20`) to prevent socket exhaustion.

---

## Tech Stack

* **Language & Runtime:** Python 3.11+, `asyncio`
* **API Framework:** FastAPI, Uvicorn
* **Data Validation:** Pydantic v2
* **Data Storage:** PostgreSQL 16 (Relational persistence), Redis 7 (In-memory caching)
* **Client Drivers:** `asyncpg` (PostgreSQL), `redis-py` (Async Redis), `websockets`
* **Containerization & CI:** Docker, Docker Compose, GitHub Actions, `pytest`

---

## Quickstart

### Prerequisites
* [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
* Python 3.11+ (if running the API locally)

### 1. Clone & Start Infrastructure
```bash
git clone [https://github.com/your-username/market-engine.git](https://github.com/your-username/market-engine.git)
cd market-engine
docker compose up -d
This starts PostgreSQL on port 5432 and Redis on port 6379.

2. Run the Application
Option A: Local Virtual Environment
Bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the API with live reload
uvicorn app.main:app --reload --port 8000
Option B: Full Docker Deployment
Bash
docker compose -f docker-compose.prod.yml up --build
API Reference
Once the server is running, interactive Swagger UI documentation is available at http://localhost:8000/docs.

Get Latest Price (Cache)
Fetches the latest tick directly from Redis.

HTTP
GET /market/{ticker}/latest
Response (200 OK):

JSON
{
  "ticker": "BTC-USD",
  "price": 64320.50,
  "volume": 0.0154,
  "timestamp": "2026-10-02T10:45:12.123456Z"
}
Get Historical Trades (Database)
Queries indexed records from PostgreSQL.

HTTP
GET /market/{ticker}/history?limit=50
Response (200 OK):

JSON
[
  {
    "price": 64320.50,
    "volume": 0.0154,
    "timestamp": "2026-10-02T10:45:12.123456Z"
  },
  {
    "price": 64319.80,
    "volume": 0.1200,
    "timestamp": "2026-10-02T10:45:11.982103Z"
  }
]
Testing
Run the test suite via pytest:

Bash
# Run unit and integration tests
pytest -v
Project Structure
Plaintext
market-engine/
├── docker-compose.yml       # Local PostgreSQL & Redis services
├── Dockerfile               # Production container definition
├── requirements.txt         # Pinned project dependencies
├── README.md                # System documentation
├── app/
│   ├── __init__.py
│   ├── main.py              # Application lifecycle & REST endpoints
│   ├── config.py            # Typed settings & environment variables
│   ├── ingestor.py          # WebSocket client & batch buffer manager
│   ├── cache.py             # Redis client wrapper
│   ├── db.py                # Schema migrations & asyncpg bulk insert
│   └── models.py            # Pydantic schemas (TradeTick)
└── tests/
    ├── __init__.py
    └── test_api.py          # Validation & endpoint tests
License
This project is licensed under the MIT License - see the LICENSE file for details.
