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
| HTTP       | httpx                             |
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

| Job              | Interval | Description                                |
| ---------------- | -------- | ------------------------------------------ |
| `ingest_all`     | 6 h      | Crawls active companies, oldest-first      |
| `enrich_pending` | 2 h      | Enriches companies with null `enriched_at` |

Configurable via `INGEST_INTERVAL_HOURS` and `ENRICH_INTERVAL_HOURS`.

## Database

### Fresh Setup

```bash
# start server (creates tables, seeds cities)
uv run uvicorn app.main:app --port 8000 --reload

# seed companies
uv run python scripts/seed.py

# enrich now (optional -- scheduler runs this on its interval)
uv run python scripts/enrich.py --all
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

| Script                    | Purpose                          |
| ------------------------- | -------------------------------- |
| `scripts/seed.py`         | Ingest all ATS sources           |
| `scripts/enrich.py --all` | Enrich all companies             |
| `scripts/validate.py`     | Validate data quality and schema |
| `scripts/test_e2e.py`     | Smoke test against a live API    |

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
