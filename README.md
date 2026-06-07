# JobDex

JobDex is a startup-focused job board built around **map-first discovery**. Instead of starting with a search box and scrolling through pages of listings, users explore opportunities geographically, browsing jobs by city, region, or remote status on an interactive map.

The platform aggregates live job postings directly from company career pages across Greenhouse, Lever, and Ashby, then normalizes them into a unified schema containing company information, role categories, seniority levels, technology keywords, location data, and city coordinates. This normalization layer enables consistent filtering and discovery across companies regardless of which applicant tracking system they use.

> Inspired by [nextdoor.company](https://nextdoor.company)

## Data Sources

| ATS        | Source                                                   |
| ---------- | -------------------------------------------------------- |
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{slug}/jobs`         |
| Lever      | `api.lever.co/v0/postings/{slug}`                        |
| Ashby      | `api.ashbyhq.com/posting-api/job-board/{slug}`           |

## Architecture

```text
┌─────────────┐     ingest     ┌──────────────────────┐
│  Greenhouse │ ─────────────► │                      │
│  Lever      │ ─────────────► │   Backend (FastAPI)  │ ──► PostgreSQL (Neon)
│  Ashby      │ ─────────────► │                      │
└─────────────┘                └──────────┬───────────┘
                                          │ REST API
                                          ▼
                               ┌──────────────────────┐
                               │      Frontend        │
                               │   Map + Listings     │
                               └──────────────────────┘
```

### Backend

- FastAPI service responsible for ATS ingestion, job normalization, and search APIs
- Aggregates jobs from Greenhouse, Lever, and Ashby
- Exposes endpoints for jobs, companies, cities, and filtering

### Frontend

- Map-first job discovery interface
- Geographic exploration of opportunities
- Listing search and filtering

### Database

- Neon serverless PostgreSQL
- SQLAlchemy-managed schema and models

## Repository Structure

```text
jobdex/
├── backend/            # FastAPI API, ingestion pipeline, data files
├── frontend/           # Frontend application
├── docker-compose.yaml
└── README.md
```

## Documentation

- `backend/README.md` - API setup, configuration, endpoints, and development workflow
- `frontend/README.md` - Frontend setup and development
