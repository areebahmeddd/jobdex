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

| ATS             | Endpoint                                                    | Status                            |
| --------------- | ----------------------------------------------------------- | --------------------------------- |
| Ashby           | `api.ashbyhq.com/posting-api/job-board/{slug}`              | ✅                                |
| Greenhouse      | `boards-api.greenhouse.io/v1/boards/{slug}/jobs`            | ✅                                |
| Lever           | `api.lever.co/v0/postings/{slug}`                           | ✅                                |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/{slug}/postings`      | ✅                                |
| Workable        | `apply.workable.com/api/v3/accounts/{slug}/jobs`            | ✅                                |
| YCombinator     | `api.ycombinator.com/v0.1/companies?q={slug}`               | ✅                                |
| Workday         | `{company}.wd{n}.myworkdayjobs.com/en-US/{board}/jobs/data` | Planned                           |
| BreezyHR        | `{slug}.breezy.hr/positions.json`                           | Not compatible                    |
| JazzHR          | `{slug}.jazz.co/api/jobs`                                   | Not compatible                    |
| Jobvite         | `jobs.jobvite.com/api/jobs`                                 | Not compatible                    |

### Europe

| ATS        | Endpoint                           | Status                         |
| ---------- | ---------------------------------- | ------------------------------ |
| Recruitee  | `{slug}.recruitee.com/api/offers/` | ✅                             |
| Personio   | `{slug}.jobs.personio.de/xml`      | Planned                        |
| Teamtailor | `api.teamtailor.com/v1/jobs`       | Planned                        |

### Middle East

| ATS        | Endpoint                           | Status                            |
| ---------- | ---------------------------------- | --------------------------------- |
| Bayt       | `bayt.com/en/company/{slug}/jobs/` | Not compatible                    |
| NaukriGulf | `naukrigulf.com/jobs-in-{country}` | Not compatible                    |
| Wuzzuf     | `wuzzuf.net/api/v1/jobs`           | Not compatible                    |

### Africa

| ATS            | Endpoint                  | Status                         |
| -------------- | ------------------------- | ------------------------------ |
| BrighterMonday | `brightermonday.com/jobs` | Not compatible                 |
| Careers24      | `careers24.com/jobs`      | Not compatible                 |
| Jobberman      | `jobberman.com/jobs`      | Not compatible                 |

### India

| ATS       | Endpoint                                                | Status                                    |
| --------- | ------------------------------------------------------- | ----------------------------------------- |
| PyjamaHR  | `api.pyjamahr.com/api/career/jobs/?company_slug={slug}` | ✅                                        |
| Freshteam | `{slug}.freshteam.com/api/open_positions`               | Planned                                   |
| Darwinbox | `{slug}.darwinbox.in/ms/candidate/careers`              | Not compatible                            |

### Australia

| ATS       | Endpoint                          | Status                              |
| --------- | --------------------------------- | ----------------------------------- |
| CareerOne | `careerone.com.au/jobs`           | Not compatible                      |
| PageUp    | `{slug}.pageuppeople.com/careers` | Not compatible                      |
| Seek      | `seek.com.au/jobs`                | Not compatible                      |

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
