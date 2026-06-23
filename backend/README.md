# Backend

FastAPI backend for JobDex. ATS ingestion, job normalisation, and REST API for search, companies, cities, and map discovery.

## Tech Stack

| Layer      | Choice                            |
| ---------- | --------------------------------- |
| API        | FastAPI + Uvicorn                 |
| ORM        | SQLAlchemy 2.0 (`Mapped[]` style) |
| Database   | Neon serverless PostgreSQL        |
| Migrations | Alembic                           |
| Config     | pydantic-settings                 |
| HTTP       | httpx2                            |
| Logging    | loguru                            |
| Scheduler  | APScheduler                       |
| Testing    | pytest                            |
| Packaging  | uv                                |
| Linting    | ruff                              |
| Deployment | Docker + Docker Compose           |

## Getting Started

### Prerequisites

- Python 3.13+
- uv
- Neon PostgreSQL project

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

Set `DATABASE_URL` to your Neon connection string.

### Running

```bash
uv run uvicorn app.main:app --port 8000 --reload
```

API: `http://localhost:8000` | Docs: `http://localhost:8000/docs`

## API

### Endpoints

| Method | Path                            | Description                |
| ------ | ------------------------------- | -------------------------- |
| `GET`  | `/health`                       | Health check               |
| `GET`  | `/`                             | Metadata and ATS providers |
| `GET`  | `/stats`                        | Platform statistics        |
| `GET`  | `/search`                       | Cross-entity search        |
| `GET`  | `/jobs`                         | Paginated jobs             |
| `GET`  | `/jobs/{id}`                    | Job detail                 |
| `GET`  | `/companies`                    | Company listing            |
| `GET`  | `/companies/{slug}`             | Company detail             |
| `GET`  | `/companies/{slug}/jobs`        | Jobs for a company         |
| `GET`  | `/cities`                       | Cities with counts         |
| `GET`  | `/cities/{slug}`                | City detail                |
| `GET`  | `/map/companies`                | Company pins               |
| `GET`  | `/map/cities`                   | City cluster pins          |
| `GET`  | `/map/companies/{slug}/offices` | Office locations           |

All endpoints are public.

### Search Filters

```http
GET /search?city=Bangalore&role=engineering&region=south_asia&is_remote=false
```

| Parameter      | Values                                                 |
| -------------- | ------------------------------------------------------ |
| `city`         | `Bangalore`, `New York`, `London`                      |
| `role`         | `engineering`, `design`, `product`, `marketing`        |
| `industry`     | `fintech`, `devtools`, `healthcare`                    |
| `country_code` | `IN`, `US`, `GB`                                       |
| `region`       | `south_asia`, `north_america`, `europe`, `middle_east` |
| `is_remote`    | `true`, `false`                                        |
| `limit`        | `20` (max `100`)                                       |
| `offset`       | `0`                                                    |

## Scheduler

Runs in-process. No separate worker needed.

| Job                 | Interval | Description                                            |
| ------------------- | -------- | ------------------------------------------------------ |
| `ingest_all`        | 6 h      | Crawls active companies, oldest-first                  |
| `enrich_pending`    | 12 h     | Enriches companies with null `enriched_at`             |
| `discover_companies`| 24 h     | Seeds new companies from ingesters with bulk discovery |

Configurable via `INGEST_INTERVAL_HOURS`, `ENRICH_INTERVAL_HOURS`, and `DISCOVER_INTERVAL_HOURS`.

## Database

### Fresh Setup

```bash
# terminal 1 — start server (runs migrations, seeds cities, starts scheduler)
uv run uvicorn app.main:app --port 8000 --reload

# terminal 2 — populate the database
uv run python scripts/discover.py        # register companies from all ingesters
uv run python scripts/probe.py           # upgrade YC companies found on Greenhouse/Ashby/Lever
uv run python scripts/ingest.py --all    # ingest jobs for all registered companies
uv run python scripts/enrich.py --all    # enrich all companies with Wikidata/Wikipedia
```

### Migrations

After modifying `app/models.py`:

```bash
# generate
uv run alembic revision --autogenerate -m "describe the change"

# apply
uv run alembic upgrade head

# rollback
uv run alembic downgrade -1
```

## Testing

Unit tests require no DB. Integration tests need `DATABASE_URL`.

```bash
uv run pytest               # all tests
uv run pytest tests/unit    # unit only
```

See `tests/README.md` for details.

## Management Scripts

| Script                           | Purpose                                                              |
| -------------------------------- | -------------------------------------------------------------------- |
| `scripts/discover.py`            | Register companies from all ingesters (YC bulk discovery)           |
| `scripts/probe.py`               | Probe YC companies against Greenhouse, Ashby, Lever; upgrade matches |
| `scripts/ingest.py --all`        | Ingest jobs for all active companies                                 |
| `scripts/ingest.py <ats> <slug>` | Ingest jobs for a single company                                     |
| `scripts/enrich.py <slug>`       | Enrich a single company with Wikidata/Wikipedia                      |
| `scripts/enrich.py --all`        | Enrich all unenriched companies                                      |
| `scripts/reset.py`               | Delete all jobs and reset company crawl state                        |
| `scripts/nuke.py`                | Drop all tables (full database wipe)                                 |

## Docker

### Docker Compose

```bash
docker compose up --build
```

Run from the repo root. Loads `backend/.env` automatically.

### Standalone Container

```bash
cd backend
docker build -t jobdex-backend .
docker run -p 8000:8000 -e DATABASE_URL="postgresql+psycopg2://..." jobdex-backend
```
