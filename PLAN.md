# JobDex — Engineering Plan

## Architecture

### Stack

| Layer       | Technology                           |
| ----------- | ------------------------------------ |
| API         | FastAPI + Uvicorn                    |
| ORM         | SQLAlchemy 2.0                       |
| Database    | Neon (serverless PostgreSQL)         |
| Migrations  | Alembic                              |
| HTTP client | httpx2 (async + tenacity retries)    |
| Scheduler   | APScheduler (in-process)             |
| Enrichment  | Wikidata · Wikipedia · Clearbit      |
| Packaging   | uv                                   |

### Ingestion Pipeline

Each ATS is a `BaseIngester` subclass with three required methods:

- `fetch_raw(slug)` — call the ATS API and return raw job dicts
- `extract_job_id(raw)` — return the stable ATS-side job identifier
- `build_job(raw, company, slug)` — normalize into an unsaved `Job` ORM object

The `ingest(slug, db)` method on `BaseIngester` orchestrates the full run:

1. **Company resolution** — look up by `ats_slug + ats_type`; fall back to `slug`; create a stub if missing.
2. **Geo-enrichment (Clearbit)** — on first ingest, query the Clearbit autocomplete API for HQ city, country, coordinates, and logo URL. Blocked or sanctioned locations are skipped.
3. **Fetch with retries** — wraps `fetch_raw` in tenacity `AsyncRetrying` with exponential backoff (min 2 s, max 30 s, 3 attempts). Retries on HTTP 429/5xx and network errors.
4. **Upsert loop** — for each raw job, compute `dedup_hash = SHA-256("{ats_type}:{slug}:{job_id}")`. New hash → `build_job` + insert. Existing hash → update `last_seen_at`.
5. **Soft-deactivation** — hashes present in the DB but absent from the latest fetch are set to `is_active = False`. Nothing is ever deleted.
6. **HQ backfill** — if the company still has no `city` after the run, the most common job city across its active listings is promoted to the company record.

### Normalizer

Applied inside each `build_job` call using data files under `backend/data/`:

| Function             | Input                         | Output                              | Data file                 |
| -------------------- | ----------------------------- | ----------------------------------- | ------------------------- |
| `classify_seniority` | job title                     | `intern/junior/mid/senior/lead/manager/director/principal/staff/executive` | `seniority_patterns.json` |
| `classify_role`      | title + department + desc     | `(category, subcategory)` tuple     | `role_patterns.json`      |
| `extract_tech_stack` | title + first 2000 ch of desc | sorted list of matched keywords     | `tech_keywords.json`      |
| `normalize_job_type` | raw ATS employment type       | `fulltime/parttime/contract/intern` | `tech_keywords.json`      |
| `canonicalize_city`  | raw location string           | canonical city name                 | `cities.json`             |

### Enrichment Pipeline

Triggered by the `enrich_pending` scheduler job and the `uv run python scripts/enrich.py` script.

1. **Wikidata** — search by company name to resolve a QID, then fetch: `founded_year`, `industry`, `HQ city`, `founders`, `key_investors`, `funding_stage`, `social_links` (Twitter, LinkedIn, Instagram, GitHub, Facebook), and `website`.
2. **Wikipedia** — if a description is unavailable from Wikidata, fetch the lead paragraph of the English Wikipedia article.
3. Existing field values are not overwritten. `enriched_at` is stamped on completion. Companies are re-enriched after `ENRICH_REFRESH_DAYS` (default: 90 days).

### Data Model

**Company** — stores both static metadata and crawl/enrichment state:

- Identity: `name`, `slug`, `logo_url`, `website`, `description`
- HQ geo: `city`, `country`, `country_code`, `region`, `latitude`, `longitude`
- Funding: `founded_year`, `funding_stage`, `total_funding_usd`, `headcount_range`, `business_model`, `founders`, `key_investors`
- ATS: `ats_type`, `ats_slug`, `last_crawled_at`, `crawl_error`, `is_active`
- Enrichment: `wikidata_id`, `enriched_at`, `social_links`, `benefits`, `office_address`

**Job** — normalized posting with full geo and role classification:

- `dedup_hash` — SHA-256, unique index, primary dedup and soft-deactivation key
- Geo: `city`, `country_code`, `region`, `latitude`, `longitude`, `is_remote`, `remote_type`
- Classification: `role_category`, `role_subcategory`, `seniority`, `job_type`, `department`, `tech_stack` (JSONB)
- Timestamps: `posted_at`, `first_seen_at`, `last_seen_at`, `is_active`
- FTS: GIN index on `to_tsvector('english', title || snippet || role_category)`, partial on `is_active = TRUE`. Partial composite indexes on `(city, role_category)`, `(region, role_category)`, `(country_code, role_category)`, `(is_remote)`, and `(posted_at)`.

### Role Categories

`role_category` is a free-text `String(100)` column with no enum constraint. Values are produced by `classify_role()` from `data/role_patterns.json`, which does first-match regex against job title and department (then description as fallback). Pattern order is significant: more specific subcategories are listed before broad catch-alls (e.g. `healthcare.medtech` fires before `engineering.general`'s `\bengineer\b`).

| Category      | Subcategories                                                                         |
| ------------- | ------------------------------------------------------------------------------------- |
| `engineering` | backend, frontend, fullstack, mobile, data, ml, devops, security, qa, embedded        |
| `data`        | scientist, analyst, bi                                                                |
| `design`      | ux, ui, product, graphic, general                                                     |
| `product`     | manager, owner, general                                                               |
| `marketing`   | growth, content, brand, general                                                       |
| `sales`       | ae, sdr, csm, general                                                                 |
| `operations`  | general                                                                               |
| `finance`     | general                                                                               |
| `legal`       | general                                                                               |
| `hr`          | recruiting, general                                                                   |
| `support`     | general                                                                               |
| `research`    | general                                                                               |
| `healthcare`  | clinical, medtech, pharma, informatics                                                |
| `hospitality` | culinary, general                                                                     |
| `other`       | general (fallback)                                                                    |

**Healthcare coverage note** — Clinical roles (nurses, doctors, physiotherapists, pharmacists) and health-adjacent roles (biomedical engineers, clinical trials, regulatory affairs, health informatics) are classified under `healthcare`. No DB migration is required; the column accepts any string value. Health-tech companies on existing ATS (Veeva → Lever, Flatiron Health → Greenhouse, Commure → Ashby) benefit from this classification automatically.

### API Surface

| Router    | Prefix       | Notes                                                                         |
| --------- | ------------ | ----------------------------------------------------------------------------- |
| jobs      | `/jobs`      | Filter by city, country_code, region, role, seniority, remote; keyset cursor pagination |
| companies | `/companies` | List, detail; ingest and enrich are triggered via scripts and the scheduler   |
| search    | `/search`    | Combinable filters (city, role, industry, region, remote) across jobs and companies |
| map       | `/map`       | Lat/lon points for companies and job clusters; supports viewport bounding box |
| cities    | `/cities`    | City list for dropdown/autocomplete                                           |
| stats     | `/stats`     | Counts by region, role category, seniority                                    |
| payments  | `/payments`  | `POST /orders` + `POST /verify` via Razorpay                                  |

### Background Jobs

| Job ID               | Interval | Purpose                                                                  |
| -------------------- | -------- | ------------------------------------------------------------------------ |
| `ingest_all`         | 6 h      | Crawl all active companies ordered by `last_crawled_at ASC NULLS FIRST`  |
| `enrich_pending`     | 12 h     | Enrich companies where `enriched_at IS NULL` or older than 90 days       |
| `discover_companies` | 24 h     | Call `discover()` on all ingesters; only YCombinator implements it today |

A `CRAWL_DELAY` of 0.3 s is inserted between each company during scheduled ingestion to avoid hammering ATS APIs.

## ATS Integrations

### Implemented

| ATS             | Region | Endpoint                                                | Method | Auth |
| --------------- | ------ | ------------------------------------------------------- | ------ | ---- |
| Ashby           | Global | `api.ashbyhq.com/posting-api/job-board/{slug}`          | GET    | None |
| Greenhouse      | Global | `boards-api.greenhouse.io/v1/boards/{slug}/jobs`        | GET    | None |
| Lever           | Global | `api.lever.co/v0/postings/{slug}`                       | GET    | None |
| SmartRecruiters | Global | `api.smartrecruiters.com/v1/companies/{slug}/postings`  | GET    | None |
| Workable        | Global | `apply.workable.com/api/v3/accounts/{slug}/jobs`        | POST   | None |
| YCombinator     | USA    | `api.ycombinator.com/v0.1/companies?q={slug}`           | GET    | None |
| Recruitee       | Europe | `{slug}.recruitee.com/api/offers/`                      | GET    | None |
| PyjamaHR        | India  | `api.pyjamahr.com/api/career/jobs/?company_slug={slug}` | GET    | None |
| MCF             | Singapore | `api.mycareersfuture.gov.sg/v2/jobs?company={slug}`  | GET    | None |

**Workable** — cursor-based POST pagination; each subsequent page is fetched with `{"nextPage": "<cursor>"}` in the request body. The list endpoint returns minimal fields; a second request to `GET api/v2/accounts/{slug}/jobs/{shortcode}` retrieves description, requirements, and benefits. Internal jobs (`isInternal: true`) are filtered out. Up to 5 detail requests run concurrently via `asyncio.Semaphore(5)`.

**Recruitee** — single GET; filter on `status == "published"`. Date format is `"YYYY-MM-DD HH:MM:SS UTC"` (not ISO 8601), parsed with `strptime`. Description falls back to `translations.en.description` if the top-level field is empty. Employment codes like `"fulltime_fixed_term"` are normalized to `"fulltime"`.

**YCombinator** — only ingester with `discover()` implemented; seeds the company list from the YC company directory.

### Planned

| ATS        | Region | Endpoint                                                    | Auth              | Blocker                                   |
| ---------- | ------ | ----------------------------------------------------------- | ----------------- | ----------------------------------------- |
| Freshteam  | India  | `{slug}.freshteam.com/api/open_positions`                   | Bearer token      | Needs per-company `ats_api_key` on schema |
| Teamtailor | Europe | `api.teamtailor.com/v1/jobs`                                | Token per company | Needs per-company `ats_api_key` on schema |
| Workday    | Global | `POST {company}.wd{n}.myworkdayjobs.com/wday/cxs/{company}/{board}/jobs` | None (unofficial) | Tenant number (`wd1`–`wd24`) and board name vary per company; must be discovered from each company's careers page URL |

Freshteam and Teamtailor both require a `company.ats_api_key` column that does not yet exist in the schema. Unblocking them means: an Alembic migration to add the column, threading the key from `Company` through `ingest()` and `fetch_raw()`, and an admin endpoint or script to register keys per company.

### Not Compatible

| ATS / Platform | Region      | Reason                                                                                                  |
| -------------- | ----------- | ------------------------------------------------------------------------------------------------------- |
| BreezyHR       | USA         | HTTP 403 on all endpoints; auth required                                                                |
| JazzHR         | USA         | `{slug}.jazz.co/api/jobs` serves SPA, no JSON                                                           |
| Jobvite        | USA         | Auth required                                                                                           |
| Wellfound      | Global      | All API endpoints 403/404; auth required                                                                |
| Welcome to the Jungle | Europe | Algolia-backed search; all `/api/v1/jobs` paths return 404                                            |
| Softgarden     | Europe      | Numeric client IDs required (not human-readable slugs); no per-company API path                         |
| Pinpoint       | Europe      | Auth required on all endpoints                                                                          |
| JOIN.com       | Europe      | v1 deprecated (410); v2 requires `Authorization` header                                                 |
| Personio       | Europe      | XML feed (`{slug}.jobs.personio.de/xml`) works for legacy customers only; newer customers use Personio's Next.js job board builder; aggressive rate limiting |
| Bayt           | Middle East | Cloudflare 403; scraping blocked                                                                        |
| GulfTalent     | Middle East | No public API; Cloudflare-protected                                                                     |
| NaukriGulf     | Middle East | DNS failure; no accessible endpoint                                                                     |
| Talentera      | Middle East | DNS failure; domain unreachable                                                                         |
| Akhtaboot      | Middle East | Elasticsearch API exists but no working per-company filter parameter                                    |
| Wuzzuf         | Middle East | Custom SSR; all `/api/v1/` paths return 404                                                             |
| Darwinbox      | India       | Angular SPA + Cloudflare Turnstile                                                                      |
| Keka HR        | India       | React SPA; no JSON on any `/careers/api/*` path                                                         |
| Instahyre      | India       | No public API                                                                                           |
| Glints         | SEA         | 403 on all endpoints                                                                                    |
| JobStreet      | SEA         | 403 (MY region); HTML SPA (PH region); Chalice API blocked                                              |
| Fuzu           | Africa      | Job board; no per-company API                                                                           |
| PNet           | Africa      | No public API                                                                                           |
| MyJobMag       | Africa      | No public API                                                                                           |

## Backlog

Platforms not yet researched. Candidates for future sprints.

- **Global / Enterprise** — iCIMS, Taleo (Oracle), SAP SuccessFactors, Bullhorn
- **Middle East** — Mihnati
- **India** — Zoho Recruit, Naukri.com, Hirect
- **Asia Pacific** — SEEK (AU/NZ), JobKorea
- **Asia Pacific (deferred)** — Kalibrr (PH/ID): `GET /api/companies/{slug}/jobs` is zero-auth JSON and structurally compatible; skipped because no active listings found across 80+ tested company slugs; revisit if platform activity recovers
- **Latin America** — Computrabajo, OCC Mundial, Catho, Bumeran
- **Specialty** — Dice, Culinary Agents
- **Healthcare** — NHS Jobs (UK): API exists at `api.jobs.nhs.uk/v1/search`; requires a free `Ocp-Apim-Subscription-Key` (Azure APIM, register at `developer.jobs.nhs.uk`). This is a single static key, not per-company, but the ingestion model is search-based rather than slug-based, which requires a fundamentally different architecture from current ingesters. All other major healthcare ATS (HealthcareSource, iCIMS, Taleo) require per-organisation auth contracts and are not feasible. Traditional clinical job boards (BioSpace, Health eCareers, Medscape Jobs) have no public JSON API.

## Adding an Ingester

### Standard (zero-auth JSON)

1. Create `backend/app/ingestion/{ats}.py` and subclass `BaseIngester`, set `ats_type`
2. Implement `fetch_raw`, `extract_job_id`, `build_job`
3. Register in `app/ingestion/__init__.py` under `INGESTERS`
4. Add unit tests in `tests/unit/test_ingesters.py`
5. Update README data sources table and PLAN.md implemented table

### Per-company credential (Freshteam, Teamtailor)

Requires a `company.ats_api_key` column (Alembic migration needed). Thread the key from `Company` into `ingest()` and `fetch_raw()`. A registration endpoint or admin script is needed to store keys per company.

### Discovery

Implement `discover()` to return unsaved `Company` stubs from the ATS company directory. Where no public directory exists, maintain a seed file at `data/companies_{ats}.json` and load it in `discover()`.
