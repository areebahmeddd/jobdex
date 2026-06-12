<p align="center">
  <img src="frontend/public/logo.svg" alt="JobDex" height="56" />
</p>

<p align="center">
  <a href="https://github.com/areebahmeddd/jobdex/releases"><img src="https://img.shields.io/github/v/release/areebahmeddd/jobdex?style=flat-square" alt="release" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="license" /></a>
</p>

<br />

Aggregates live job postings from Greenhouse, Lever, and Ashby into a unified schema and plots them on an interactive world map. Filter by city, region, industry, or role to explore where startups are hiring without the noise of traditional job boards.

> Open source alternative to [nextdoor.company](https://nextdoor.company)

## Architecture

```text
┌─────────────┐     ingest     ┌──────────────────────┐
│  Greenhouse │ ─────────────► │                      │
│  Lever      │ ─────────────► │   Backend (FastAPI)  │ ──► PostgreSQL
│  Ashby      │ ─────────────► │                      │
└─────────────┘                └──────────┬───────────┘
                                          │ REST API
                                          ▼
                               ┌──────────────────────┐
                               │   Frontend (React)   │
                               │   Map + Discovery    │
                               └──────────────────────┘
```

## Data Sources

| ATS        | Endpoint                                              |
| ---------- | ----------------------------------------------------- |
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{slug}/jobs`      |
| Lever      | `api.lever.co/v0/postings/{slug}`                     |
| Ashby      | `api.ashbyhq.com/posting-api/job-board/{slug}`        |

## Getting Started

```bash
git clone https://github.com/areebahmeddd/jobdex
cd jobdex
docker compose up
```

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Documentation

- `backend/README.md` - API setup, configuration, endpoints, and ingestion
- `frontend/README.md` - Frontend setup and development
