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

### USA

| ATS             | Endpoint                                                              | Status  |
| --------------- | --------------------------------------------------------------------- | ------- |
| Ashby           | `api.ashbyhq.com/posting-api/job-board/{slug}`                        | ✅      |
| BreezyHR        | `{slug}.breezy.hr/positions.json`                                     | Planned |
| Greenhouse      | `boards-api.greenhouse.io/v1/boards/{slug}/jobs`                      | ✅      |
| JazzHR          | `{slug}.jazz.co/api/jobs`                                             | Planned |
| Lever           | `api.lever.co/v0/postings/{slug}`                                     | ✅      |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/{slug}/postings`                | ✅      |
| Workable        | `apply.workable.com/{slug}/api/v3/jobs`                               | Planned |
| YCombinator     | `api.ycombinator.com/v0.1/companies?q={slug}`                         | ✅      |

### Europe

| ATS        | Endpoint                              | Status  |
| ---------- | ------------------------------------- | ------- |
| Personio   | `{slug}.jobs.personio.de/xml`         | Planned |
| Recruitee  | `{slug}.recruitee.com/api/offers`     | Planned |
| Teamtailor | `api.teamtailor.com/v1/jobs`          | Planned |

### Middle East

| ATS        | Endpoint                              | Status  |
| ---------- | ------------------------------------- | ------- |
| Bayt       | `bayt.com/en/company/{slug}/jobs/`    | Planned |
| GulfTalent | `gulftalent.com/jobs`                 | Planned |
| NaukriGulf | `naukrigulf.com/jobs-in-{country}`    | Planned |

### India

| ATS       | Endpoint                                                        | Status  |
| --------- | --------------------------------------------------------------- | ------- |
| Darwinbox | `{slug}.darwinbox.in/ms/candidate/careers`                      | Planned |
| Freshteam | `{slug}.freshteam.com/api/open_positions`                       | Planned |
| PyjamaHR  | `api.pyjamahr.com/api/career/jobs/?company_slug={slug}`         | ✅      |

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
