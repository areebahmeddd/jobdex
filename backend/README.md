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
| Linting & Formatting  | ruff + pre-commit                 |
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

At minimum, configure:

- `DATABASE_URL`
- `ADMIN_API_KEY`

You can create a Neon project and retrieve a connection string using:

```bash
neon projects create --name jobdex --region-id aws-ap-southeast-1
neon connection-string
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
  -e DATABASE_URL="postgresql+asyncpg://..." \
  -e ADMIN_API_KEY="your-key" \
  jobdex-backend
```

## API

### Endpoints

| Method | Path                      | Auth | Description                        |
| ------ | ------------------------- | ---- | ---------------------------------- |
| `GET`  | `/health`                 |      | Health check                       |
| `GET`  | `/`                       |      | Supported ATS providers            |
| `GET`  | `/search`                 |      | Map-first job discovery            |
| `GET`  | `/jobs`                   |      | Paginated job listing              |
| `GET`  | `/jobs/{id}`              |      | Job details                        |
| `GET`  | `/companies`              |      | Company listing                    |
| `GET`  | `/companies/{slug}`       |      | Company details and active jobs    |
| `GET`  | `/cities`                 |      | Cities with job and company counts |
| `GET`  | `/stats`                  |      | Aggregate platform statistics      |
| `POST` | `/ingest/{ats}/{slug}`    | ✓    | Ingest a job board                 |
| `POST` | `/ingest/discover/{slug}` | ✓    | Auto-detect ATS and ingest         |
| `POST` | `/admin/reset`            | ✓    | Clear all jobs (development only)  |

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
| `page`         | `1`                                                    |
| `limit`        | `20`                                                   |

### Ingesting Job Boards

```bash
# Greenhouse
curl -X POST http://localhost:8000/ingest/greenhouse/airbnb \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Lever
curl -X POST http://localhost:8000/ingest/lever/spotify \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Ashby
curl -X POST http://localhost:8000/ingest/ashby/linear \
  -H "X-API-Key: <ADMIN_API_KEY>"

# Auto-detect
curl -X POST http://localhost:8000/ingest/discover/notion \
  -H "X-API-Key: <ADMIN_API_KEY>"
```

## Configuration Reference

All settings are loaded from `.env`.

| Variable                 | Default                         | Description                            |
| ------------------------ | ------------------------------- | -------------------------------------- |
| `DATABASE_URL`           | `postgresql://localhost/jobdex` | PostgreSQL connection string           |
| `DB_ECHO`                | `false`                         | Enable SQL query logging               |
| `HTTP_TIMEOUT`           | `30.0`                          | ATS request timeout in seconds         |
| `CRAWL_DELAY`            | `0.3`                           | Delay between ATS requests             |
| `GEOCODE_UNKNOWN_CITIES` | `false`                         | Geocode unknown cities using Nominatim |
| `GEOCODE_USER_AGENT`     | `jobdex-api/1.0`                | User-Agent sent to Nominatim           |
| `ADMIN_API_KEY`          | Unset                           | Protect admin and ingestion routes     |
| `DEBUG`                  | `false`                         | FastAPI debug mode                     |

## Project Structure

```text
backend/
├── app/
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── ingestion/
│   └── routers/
├── data/
│   ├── cities.json
│   ├── role_patterns.json
│   ├── seniority_patterns.json
│   └── tech_keywords.json
├── scripts/
│   ├── seed.py
│   └── validate.py
├── .env.example
├── Dockerfile
├── pyproject.toml
└── README.md
```

### Directory Overview

- `app/` - FastAPI application code
- `app/ingestion/` - ATS-specific ingestion clients
- `app/routers/` - API route handlers
- `data/` - Normalization datasets and lookup files
- `scripts/` - Development and operational utilities

## Development

### Validation

Run the integration suite against a local instance:

```bash
uv run python scripts/validate.py --api-key <ADMIN_API_KEY>
```

Against a remote deployment:

```bash
uv run python scripts/validate.py \
  --base-url https://your-server.example.com \
  --api-key <ADMIN_API_KEY>
```

### Pre-commit Hooks

Install hooks:

```bash
uv run pre-commit install
```

Run manually:

```bash
uv run pre-commit run --all-files
```

Configured hooks:

- end-of-file-fixer
- trailing-whitespace
- check-json
- check-yaml
- ruff check --fix
- ruff format
