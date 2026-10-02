# Real-Time Market Ingestion & Caching Engine

[![Status](https://img.shields.io/badge/Status-In%20Development%20%2F%20Bootstrap-orange.svg)](#project-roadmap)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An asynchronous, event-driven market data pipeline built with Python, FastAPI, Redis, and PostgreSQL. The system is designed to consume live WebSocket trade feeds (such as Coinbase Pro), maintain a sub-5ms in-memory cache in Redis for real-time reads, and persist batched time-series records into PostgreSQL using high-throughput binary copy protocols.

> [!NOTE]
> **Project Status:** This project is currently in the initial bootstrap phase. The system architecture, non-functional requirements, data schemas, and dependencies are established. Core services and pipeline components are under active development.

---

## Architecture Overview

```text
                  ┌──────────────────────────────────────┐
                  │   Coinbase Pro / Finnhub WebSocket   │
                  │           (WSS Feed)                 │
                  └──────────────────┬───────────────────┘
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
```

For the full architectural specification, refer to the [System Design Document](docs/system_design.md).

---

## Key Design Principles

* **Decoupled Hot Reads & Batch Writes:** Incoming trade ticks immediately update Redis with a 60-second TTL to deliver sub-5ms response times on `/market/{ticker}/latest` while isolating the persistent store from read spikes.
* **Micro-Batch Database Flushing:** Ticks are buffered in-memory and flushed to PostgreSQL in batches (every 5 seconds or 50 records) via `asyncpg` binary copy protocols (`copy_records_to_table`) to minimize lock contention and I/O bottlenecks.
* **Bounded Connection Pooling:** Database and cache access use managed connection pools to prevent socket exhaustion under high load.

---

## Tech Stack

* **Language & Runtime:** Python 3.11+, `asyncio`
* **API Framework:** FastAPI, Uvicorn
* **Data Validation:** Pydantic v2
* **In-Memory Caching:** Redis 7 (Alpine)
* **Relational Storage:** PostgreSQL 16
* **Database Drivers:** `asyncpg` (PostgreSQL), `redis-py` (Async Redis), `websockets`
* **Containerization & Testing:** Docker, Docker Compose, `pytest`, `pytest-asyncio`

---

## Project Roadmap

- [x] **Sprint 0: Architecture & Bootstrap**
  - [x] System design & low-latency architecture blueprint ([docs/system_design.md](docs/system_design.md))
  - [x] Initial repository structure and dependency definition (`requirements.txt`)
  - [x] Git workflow and environment configuration
- [ ] **Sprint 1: Core Data Layer**
  - [ ] Pydantic tick schemas (`app/models.py`)
  - [ ] Redis caching client with TTL management (`app/cache.py`)
  - [ ] PostgreSQL schema & `asyncpg` connection pool setup (`app/db.py`)
- [ ] **Sprint 2: Ingestion Engine**
  - [ ] WebSocket streaming client with auto-reconnect backoff (`app/ingestor.py`)
  - [ ] Micro-batch queue & asynchronous flusher
- [ ] **Sprint 3: API & Orchestration**
  - [ ] FastAPI application lifecycle and endpoints (`app/main.py`)
  - [ ] Docker Compose orchestration (`postgres`, `redis`, `api`)
  - [ ] Automated unit and integration test suite (`tests/`)

---

## Planned Directory Structure

```text
FinanceIngestor/
├── .gitignore               # Environment and artifact exclusions
├── README.md                # Project overview and instructions
├── requirements.txt         # Core Python dependencies
├── docs/
│   └── system_design.md     # In-depth system design & latency benchmarks
├── docker-compose.yml       # Local PostgreSQL & Redis infrastructure (Planned)
├── Dockerfile               # Application container definition (Planned)
├── app/                     # Application source code (In Progress)
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point & endpoints
│   ├── config.py            # Environment settings & config
│   ├── models.py            # Pydantic data models
│   ├── ingestor.py          # WebSocket ingestion worker & batch buffer
│   ├── cache.py             # Async Redis caching wrapper
│   └── db.py                # PostgreSQL pool & bulk insert logic
└── tests/                   # Test suite (Planned)
    ├── __init__.py
    ├── test_models.py
    └── test_api.py
```

---

## Planned API Reference

Once the REST server is implemented, interactive OpenAPI documentation will be hosted at `http://localhost:8000/docs`.

### 1. Get Latest Price (Cache Tier)
Pulls the latest cached trade tick directly from Redis.

```http
GET /market/{ticker}/latest
```

**Response (`200 OK`):**
```json
{
  "ticker": "BTC-USD",
  "price": 64320.50,
  "volume": 0.0154,
  "timestamp": "2026-10-02T10:45:12.123456Z"
}
```

### 2. Get Historical Trades (Persistent Tier)
Queries indexed historical records from PostgreSQL.

```http
GET /market/{ticker}/history?limit=50
```

**Response (`200 OK`):**
```json
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
```

---

## Getting Started (Current Phase)

### 1. Clone the Repository
```bash
git clone https://github.com/MrKK619/financeingest.git
cd FinanceIngestor
```

### 2. Setup Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Activate on Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
