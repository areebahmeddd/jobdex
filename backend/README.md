# Backend

FastAPI backend for JobDex. Handles ATS ingestion, job normalization, PostgreSQL persistence, and the REST API powering search, companies, cities, and map-based job discovery.

## Tech Stack

| Layer                 | Choice                            |
| --------------------- | --------------------------------- |
| API                   | FastAPI + Uvicorn                 |
| ORM                   | SQLAlchemy 2.0 (`Mapped[]` style) |
| Database              | Neon serverless PostgreSQL        |
| Configuration         | pydantic-settings                 |
| HTTP Client           | httpx                             |
| Logging               | loguru                            |
| Dependency Management | uv                                |
| Linting / Formatting  | ruff                              |
| Deployment            | Docker + Docker Compose           |

## Getting Started

### Prerequisites

- Python 3.13+
- uv
- Neon PostgreSQL project (free tier is sufficient)

### Installation

```bash
git clone <repo-url>
cd jobdex/backend
uv sync
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env` and set `DATABASE_URL` to your Neon connection string.

### Running Locally

```bash
uv run uvicorn app.main:app --port 8000 --reload
```

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

### Fresh Database Workflow

Complete setup from a blank database:

```bash
# 1. Start the server - creates tables, seeds cities, and starts the scheduler
uv run uvicorn app.main:app --port 8000 --reload

# 2. In a second terminal: seed all configured companies (talks to DB directly, no HTTP)
uv run python scripts/seed.py

# 3. Optional: enrich all companies now rather than waiting for the scheduler
uv run python scripts/enrich.py --all
```

After step 1 the scheduler is running. Once `seed.py` populates the companies, the scheduler re-crawls them automatically every 6 hours.

## Docker

### Docker Compose

Run from the repository root:

```bash
docker compose up --build
```

The compose configuration automatically loads `backend/.env`.

### Standalone Container

```bash
cd backend
docker build -t jobdex-backend .
docker run -p 8000:8000 -e DATABASE_URL="postgresql+psycopg2://..." jobdex-backend
```

## API

### Endpoints

| Method | Path                     | Description                        |
| ------ | ------------------------ | ---------------------------------- |
| `GET`  | `/health`                | Health check                       |
| `GET`  | `/`                      | Supported ATS providers            |
| `GET`  | `/search`                | Cross-entity job discovery         |
| `GET`  | `/jobs`                  | Paginated job listing              |
| `GET`  | `/jobs/{id}`             | Job detail                         |
| `GET`  | `/companies`             | Company listing                    |
| `GET`  | `/companies/{slug}`      | Company detail                     |
| `GET`  | `/companies/{slug}/jobs` | Paginated jobs for a company       |
| `GET`  | `/cities`                | Cities with job and company counts |
| `GET`  | `/cities/{slug}`         | City detail                        |
| `GET`  | `/map/companies`         | Company map pins                   |
| `GET`  | `/map/cities`            | City cluster map pins              |
| `GET`  | `/stats`                 | Aggregate platform statistics      |

No authentication is required for any endpoint.

### Search Filters

```http
GET /search?city=Bangalore&role=engineering&region=south_asia&is_remote=false
```

| Parameter      | Example Values                                         |
| -------------- | ------------------------------------------------------ |
| `city`         | `Bangalore`, `New York`, `London`                      |
| `role`         | `engineering`, `design`, `product`, `marketing`        |
| `industry`     | `fintech`, `devtools`, `healthcare`                    |
| `country_code` | `IN`, `US`, `GB`                                       |
| `region`       | `south_asia`, `north_america`, `europe`, `middle_east` |
| `is_remote`    | `true`, `false`                                        |
| `limit`        | `20`                                                   |
| `offset`       | `0`                                                    |

### Scheduler

The scheduler runs inside the server process - no separate worker, queue, or terminal needed.

When `uvicorn` starts, the `lifespan` hook launches an `AsyncIOScheduler` that fires two background jobs:

| Job              | Default interval | What it does                                                            |
| ---------------- | ---------------- | ------------------------------------------------------------------------|
| `ingest_all`     | Every 6 hours    | Crawls all active companies, ordered by oldest `last_crawled_at`        |
| `enrich_pending` | Every 2 hours    | Enriches any company with a null `enriched_at` via Wikidata + Wikipedia |

Both intervals are configurable via `INGEST_INTERVAL_HOURS` and `ENRICH_INTERVAL_HOURS` in `.env`.

### Management Scripts

For one-off operations that run directly against the database - no server needed:

```bash
# Ingest a single company board
uv run python scripts/ingest.py greenhouse airbnb
uv run python scripts/ingest.py lever netflix
uv run python scripts/ingest.py ashby linear

# Auto-detect ATS provider and ingest
uv run python scripts/discover.py notion

# Enrich a single company
uv run python scripts/enrich.py stripe

# Enrich all unenriched companies
uv run python scripts/enrich.py --all

# Wipe all jobs and reset crawl state (keeps companies and cities)
uv run python scripts/reset.py
```

## Configuration

All settings are loaded from `.env`.

| Variable                 | Default                         | Description                           |
| ------------------------ | ------------------------------- | ------------------------------------- |
| `DATABASE_URL`           | `postgresql://localhost/jobdex` | PostgreSQL connection string          |
| `DB_ECHO`                | `false`                         | Enable SQL query logging              |
| `DB_POOL_SIZE`           | `2`                             | SQLAlchemy connection pool size       |
| `DB_MAX_OVERFLOW`        | `3`                             | Max connections above pool size       |
| `DB_POOL_TIMEOUT`        | `30`                            | Seconds to wait for a connection      |
| `DB_POOL_RECYCLE`        | `600`                           | Seconds before recycling a connection |
| `HTTP_TIMEOUT`           | `30.0`                          | ATS request timeout in seconds        |
| `CRAWL_DELAY`            | `0.3`                           | Delay between ATS requests            |
| `GEOCODE_UNKNOWN_CITIES` | `false`                         | Geocode unknown cities via Nominatim  |
| `GEOCODE_USER_AGENT`     | `jobdex-api/1.0`                | User-Agent sent to Nominatim          |
| `INGEST_INTERVAL_HOURS`  | `6`                             | Scheduler re-crawl interval (hours)   |
| `ENRICH_INTERVAL_HOURS`  | `2`                             | Scheduler enrichment interval (hours) |
| `DEBUG`                  | `false`                         | FastAPI debug mode                    |

## Development

Run the E2E test suite against a local instance:

```bash
uv run python scripts/test_e2e.py
```

Against a remote deployment:

```bash
uv run python scripts/test_e2e.py --base-url https://your-server.example.com
```
