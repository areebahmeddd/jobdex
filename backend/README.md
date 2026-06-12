# Backend

FastAPI backend for JobDex. Handles ATS ingestion, job normalization, PostgreSQL persistence, and the REST API powering search, companies, cities, and map-based job discovery.

## Tech Stack

| Layer                 | Choice                            |
| --------------------- | --------------------------------- |
| API                   | FastAPI + Uvicorn                 |
| ORM                   | SQLAlchemy 2.0 (`Mapped[]` style) |
| Database              | Neon serverless PostgreSQL (18)   |
| Configuration         | pydantic-settings                 |
| HTTP Client           | httpx                             |
| Logging               | loguru                            |
| Dependency Management | uv                                |
| Linting & Formatting  | ruff                              |
| Deployment            | Docker + Docker Compose           |

## Getting Started

### Prerequisites

- Python 3.11+
- uv
- Neon PostgreSQL project (free tier is sufficient)

### Installation

```bash
git clone <repo-url>
cd jobdex/backend
uv sync
```

### Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

### Running Locally

```bash
uv run uvicorn app.main:app --port 8000 --reload
```

Available endpoints:

- API: `http://localhost:8000`
- Documentation: `http://localhost:8000/docs`

### Seed Sample Data

```bash
uv run python scripts/seed.py --api-key <ADMIN_API_KEY>
```

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

docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql+psycopg2://..." \
  -e ADMIN_API_KEY="your-key" \
  jobdex-backend
```

## API

### Endpoints

| Method | Path                            | Auth | Description                        |
| ------ | ------------------------------- | ---- | ---------------------------------- |
| `GET`  | `/health`                       |      | Health check                       |
| `GET`  | `/`                             |      | Supported ATS providers            |
| `GET`  | `/search`                       |      | Cross-entity job discovery         |
| `GET`  | `/jobs`                         |      | Paginated job listing              |
| `GET`  | `/jobs/{id}`                    |      | Job detail                         |
| `GET`  | `/companies`                    |      | Company listing                    |
| `GET`  | `/companies/{slug}`             |      | Company detail                     |
| `GET`  | `/companies/{slug}/jobs`        |      | Paginated jobs for a company       |
| `GET`  | `/cities`                       |      | Cities with job and company counts |
| `GET`  | `/cities/{slug}`                |      | City detail                        |
| `GET`  | `/map/companies`                |      | Company map pins                   |
| `GET`  | `/map/cities`                   |      | City cluster map pins              |
| `GET`  | `/admin/stats`                  | ✓    | Aggregate platform statistics      |
| `POST` | `/admin/ingest/{ats}/{slug}`    | ✓    | Ingest a job board                 |
| `POST` | `/admin/ingest/discover/{slug}` | ✓    | Auto-detect ATS and ingest         |
| `POST` | `/admin/reset`                  | ✓    | Clear all jobs (development only)  |

Protected routes require:

```text
X-API-Key: <ADMIN_API_KEY>
```

### Search Filters

Example:

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

### Ingesting Job Boards

```bash
# Greenhouse
curl -X POST http://localhost:8000/admin/ingest/greenhouse/airbnb \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Lever
curl -X POST http://localhost:8000/admin/ingest/lever/spotify \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Ashby
curl -X POST http://localhost:8000/admin/ingest/ashby/linear \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Auto-detect
curl -X POST http://localhost:8000/admin/ingest/discover/notion \
  -H "X-API-Key: <ADMIN_API_KEY>"
```

## Configuration Reference

All settings are loaded from `.env`.

| Variable                 | Default                         | Description                            |
|--------------------------|---------------------------------|----------------------------------------|
| `DATABASE_URL`           | `postgresql://localhost/jobdex` | PostgreSQL connection string           |
| `DB_ECHO`                | `false`                         | Enable SQL query logging               |
| `DB_POOL_SIZE`           | `2`                             | SQLAlchemy connection pool size        |
| `DB_MAX_OVERFLOW`        | `3`                             | Max connections above pool size        |
| `DB_POOL_TIMEOUT`        | `30`                            | Seconds to wait for a connection       |
| `DB_POOL_RECYCLE`        | `600`                           | Seconds before recycling a connection  |
| `HTTP_TIMEOUT`           | `30.0`                          | ATS request timeout in seconds         |
| `CRAWL_DELAY`            | `0.3`                           | Delay between ATS requests             |
| `GEOCODE_UNKNOWN_CITIES` | `false`                         | Geocode unknown cities using Nominatim |
| `GEOCODE_USER_AGENT`     | `jobdex-api/1.0`                | User-Agent sent to Nominatim           |
| `ADMIN_API_KEY`          | `Unset`                         | Protect admin and ingestion routes     |
| `DEBUG`                  | `false`                         | FastAPI debug mode                     |

## Development

### Validation

Run the E2E test suite against a local instance:

```bash
uv run python scripts/test_e2e.py
```

Against a remote deployment:

```bash
uv run python scripts/test_e2e.py \
  --base-url https://your-server.example.com
```
