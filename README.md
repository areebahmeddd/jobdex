<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="frontend/public/logo-dark.svg" />
    <img src="frontend/public/logo-light.svg" alt="JobDex" height="56" />
  </picture>
</p>

<p align="center">
  <a href="https://github.com/areebahmeddd/jobdex/releases"><img src="https://img.shields.io/github/v/release/areebahmeddd/jobdex?style=flat-square" alt="release" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="license" /></a>
</p>

<br />

JobDex is a startup-focused job board built around map-first discovery. Instead of starting with a search box and scrolling through pages of listings, users explore opportunities geographically, browsing jobs by city, region, or remote status on an interactive map.

> Open source alternative to [nextdoor.company](https://nextdoor.company)

## Architecture

<p align="center">
  <img src="docs/architecture.png" alt="JobDex Architecture" />
</p>

## Data Sources

| ATS          | Endpoint                                                       |
| ------------ | -------------------------------------------------------------- |
| Ashby        | `api.ashbyhq.com/posting-api/job-board/{slug}`                 |
| Greenhouse   | `boards-api.greenhouse.io/v1/boards/{slug}/jobs`               |
| Lever        | `api.lever.co/v0/postings/{slug}`                              |
| YCombinator  | `api.ycombinator.com/v0.1/companies?q={slug}`                  |

## Production

| Service      | URL                                  |
| ------------ | ------------------------------------ |
| Frontend UI  | <https://jobdex.1mindlabs.org>       |
| Backend API  | <https://jobdex-api.1mindlabs.org>   |

## Getting Started

```bash
git clone https://github.com/areebahmeddd/jobdex
cd jobdex
docker compose up
```

- Frontend UI: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Documentation

- `backend/README.md` - API setup, configuration, endpoints, and ingestion
- `frontend/README.md` - Frontend setup and development
