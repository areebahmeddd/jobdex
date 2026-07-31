# JobDex: Engineering Plan

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

Each ATS is a `BaseIngester` subclass with three required methods, plus one optional hook:

- `fetch_raw(slug)`: call the ATS API and return raw job dicts
- `extract_job_id(raw)`: return the stable ATS-side job identifier, from the list payload alone
- `build_job(raw, company, slug)`: normalize into an unsaved `Job` ORM object
- `hydrate(raw_jobs, slug)`: optional, fetch per-job detail for postings about to be inserted

The `ingest(slug, db)` method on `BaseIngester` orchestrates the full run:

1. **Company resolution**: look up by `ats_slug + ats_type`; fall back to `slug`; create a stub if missing.
2. **Geo-enrichment (Clearbit)**: on first ingest, query the Clearbit autocomplete API for HQ city, country, coordinates, and logo URL. Blocked or sanctioned locations are skipped.
3. **Fetch with retries**: wraps `fetch_raw` in tenacity `AsyncRetrying` with exponential backoff (min 2 s, max 30 s, 3 attempts). Retries on HTTP 429/5xx and network errors.
4. **Split**: for each raw job, compute `dedup_hash = SHA-256("{ats_type}:{slug}:{job_id}")`. Known hashes have `last_seen_at` refreshed in chunked bulk updates; a hash repeated inside one response is counted once.
5. **Hydrate**: `hydrate()` runs over the new postings only, so per-job detail requests scale with what changed rather than board size.
6. **Insert**: `build_job` each hydrated posting and add it. Blocked locations are dropped and excluded from the seen set, so they never look like closures.
7. **Soft-deactivation**: hashes present in the DB but absent from the latest fetch are set to `is_active = False`. Nothing is ever deleted.
8. **HQ backfill**: if the company still has no `city` after the run, the most common job city across its active listings is promoted to the company record.

### Normalizer

Applied inside each `build_job` call using data files under `backend/data/`:

| Function             | Input                         | Output                              | Data file                 |
| -------------------- | ----------------------------- | ----------------------------------- | ------------------------- |
| `classify_seniority` | job title                     | `intern/junior/mid/senior/lead/manager/director/principal/staff/executive` | `seniority_patterns.json` |
| `classify_role`      | title + department + desc     | `(category, subcategory)` tuple     | `role_patterns.json`      |
| `extract_tech_stack` | title + first 2000 ch of desc | sorted list of matched keywords     | `tech_keywords.json`      |
| `normalize_job_type` | raw ATS employment type       | `fulltime/parttime/contract/intern` | `tech_keywords.json`      |
| `canonicalize_city`  | raw location string           | canonical city name                 | `cities.json`             |
| `get_country_code_for_name` | country display name   | ISO-2 country code                  | derived from `cities.json` |

`get_country_code_for_name` covers ATS that report a country as a display name with no ISO code (Workday sends `{"descriptor": "United States of America"}`). Without it, any job whose city falls outside the 135-entry city table is stored with no `country_code` and therefore no `region`, leaving it out of region filters, `/stats`, and the map. The lookup is built from the `country`/`country_code` pairs already in `cities.json`, plus a short alias table for long-form names that file does not carry (`United States of America`, `England`, `Czechia`).

Measured on NVIDIA's Workday board (2000 jobs), `country_code` and `region` coverage went from 450 to 2000. City coverage is unchanged at 460 and is bounded by the city table, not the ingester; `GEOCODE_UNKNOWN_CITIES` is the existing escape hatch. It also fixed a gap in location blocking: 317 Israel-based postings resolved to `country_code = None` because their cities are not in the table, so they passed `is_blocked_location`. They now match on `IL` and are skipped.

### Enrichment Pipeline

Triggered by the `enrich_pending` scheduler job and the `uv run python scripts/enrich.py` script.

1. **Wikidata**: search by company name to resolve a QID, then fetch: `founded_year`, `industry`, `HQ city`, `founders`, `key_investors`, `funding_stage`, `social_links` (Twitter, LinkedIn, Instagram, GitHub, Facebook), and `website`.
2. **Wikipedia**: if a description is unavailable from Wikidata, fetch the lead paragraph of the English Wikipedia article.
3. Existing field values are not overwritten. `enriched_at` is stamped on completion. Companies are re-enriched after `ENRICH_REFRESH_DAYS` (default: 90 days).

### Data Model

**Company**: stores both static metadata and crawl/enrichment state:

- Identity: `name`, `slug`, `logo_url`, `website`, `description`
- HQ geo: `city`, `country`, `country_code`, `region`, `latitude`, `longitude`
- Funding: `founded_year`, `funding_stage`, `total_funding_usd`, `headcount_range`, `business_model`, `founders`, `key_investors`
- ATS: `ats_type`, `ats_slug`, `last_crawled_at`, `crawl_error`, `is_active`
- Enrichment: `wikidata_id`, `enriched_at`, `social_links`, `benefits`, `office_address`

**Job**: normalized posting with full geo and role classification:

- `dedup_hash`: SHA-256, unique index, primary dedup and soft-deactivation key
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

**Healthcare coverage note**: Clinical roles (nurses, doctors, physiotherapists, pharmacists) and health-adjacent roles (biomedical engineers, clinical trials, regulatory affairs, health informatics) are classified under `healthcare`. No DB migration is required; the column accepts any string value. Health-tech companies on existing ATS (Veeva → Lever, Flatiron Health → Greenhouse, Commure → Ashby) benefit from this classification automatically.

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
| `ingest_all`         | 15 min   | Crawl the `INGEST_BATCH_SIZE` least recently crawled companies, ordered by `last_crawled_at ASC NULLS FIRST` |
| `enrich_pending`     | 12 h     | Enrich companies where `enriched_at IS NULL` or older than 90 days       |
| `discover_companies` | 24 h     | Call `discover()` on all ingesters. YCombinator crawls the live YC directory; Workday, Teamtailor, and Rippling return stubs from their `data/companies_{ats}.json` seed files |

A `CRAWL_DELAY` of 0.3 s is inserted between each company during scheduled ingestion to avoid hammering ATS APIs.

**Bounded ticks.** Ingestion is a rotating queue rather than a full sweep. The ordering already puts the stalest company first, so a capped batch still reaches everything: companies covered per day is `(1440 / INGEST_INTERVAL_MINUTES) * INGEST_BATCH_SIZE`, or 2400/day at the defaults. A tick that dies part way through only loses its own slice, because the companies it never reached keep their old `last_crawled_at` and sort first next time. `scripts/ingest.py --all` passes `batch_size=0` for an unbounded seed run.

**One runner at a time.** Each replica runs its own APScheduler, so `max_instances=1` is not enough on its own. Every scheduled job runs behind a Postgres advisory lock (`pg_try_advisory_lock`); a replica that cannot take the lock skips the tick. `migrate_db()` uses the blocking form so simultaneous boots serialise on `alembic_version` instead of racing, and `scripts/ingest.py --all` takes the same ingest lock so a local seed run cannot overlap a deployed crawler.

### Hydration

`build_job()` only ever runs for postings whose `dedup_hash` is not already stored; known postings just get `last_seen_at` bumped. Fetching per-job detail for the whole board therefore threw away almost all of it once a board was seeded.

`BaseIngester.hydrate(raw_jobs, slug)` is called from `ingest()` after the new/known split, so the ATS that need a second request per job (Workday, Workable, PyjamaHR, Rippling) pay only for postings about to be inserted. `fetch_raw()` returns the list payload alone. All four can derive `extract_job_id` from that list payload, which is what makes the split possible. Implementations must return one entry per input in the same order; a length mismatch is logged and the un-hydrated payloads are used rather than dropping postings. The default is a no-op.

Measured against GSK's Workday board (698 jobs): a full crawl was 41 s of listing plus ~107 s of detail; in steady state it is 41 s plus ~2 s.

## ATS Integrations

### Implemented

| ATS             | Region | Endpoint                                                | Method | Auth |
| --------------- | ------ | ------------------------------------------------------- | ------ | ---- |
| Ashby           | Global | `api.ashbyhq.com/posting-api/job-board/{slug}`          | GET    | None |
| Greenhouse      | Global | `boards-api.greenhouse.io/v1/boards/{slug}/jobs`        | GET    | None |
| Lever           | Global | `api.lever.co/v0/postings/{slug}`                       | GET    | None |
| SmartRecruiters | Global | `api.smartrecruiters.com/v1/companies/{slug}/postings`  | GET    | None |
| Workable        | Global | `apply.workable.com/api/v3/accounts/{slug}/jobs`        | POST   | None |
| Workday         | Global | `{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{board}/jobs` | POST | None |
| Rippling        | Global | `api.rippling.com/platform/api/ats/v1/board/{slug}/jobs` | GET    | None |
| YCombinator     | USA    | `api.ycombinator.com/v0.1/companies?q={slug}`           | GET    | None |
| Recruitee       | Europe | `{slug}.recruitee.com/api/offers/`                      | GET    | None |
| Teamtailor      | Europe | `{slug}.teamtailor.com/jobs.json`                       | GET    | None |
| PyjamaHR        | India  | `api.pyjamahr.com/api/career/jobs/?company_slug={slug}` | GET    | None |
| MCF             | Singapore | `api.mycareersfuture.gov.sg/v2/jobs?company={slug}`  | GET    | None |

**Workable**: cursor-based POST pagination; each subsequent page is fetched with `{"nextPage": "<cursor>"}` in the request body. The list endpoint returns minimal fields; `hydrate()` issues `GET api/v2/accounts/{slug}/jobs/{shortcode}` for description, requirements, and benefits. Internal jobs (`isInternal: true`) are filtered out. Up to 5 detail requests run concurrently via `asyncio.Semaphore(5)`.

**Recruitee**: single GET; filter on `status == "published"`. Date format is `"YYYY-MM-DD HH:MM:SS UTC"` (not ISO 8601), parsed with `strptime`. Description falls back to `translations.en.description` if the top-level field is empty. Employment codes like `"fulltime_fixed_term"` are normalized to `"fulltime"`.

**Workday**: the CXS endpoint needs no auth but is addressed by three per-customer values that cannot be derived from the company name: the tenant, the data-centre number (`wd1` to `wd12`), and the board name. They are packed into `ats_slug` as `tenant:wdN:board`, so no schema change is needed; `_resolve_company` is overridden to keep `Company.slug` as the bare tenant. Three API quirks shape the paging loop: `limit` above 20 returns HTTP 400, `total` is populated only on the first page and reports `0` after it, and an offset past the last page wraps around and re-serves page 0. Paging therefore stops on the first-page total, a short page, or a page with no new `externalPath`, capped at 100 pages (2000 jobs). The list payload has no description or absolute date, so `hydrate()` issues `GET .../{board}{externalPath}` for `jobDescription`, `timeType`, and `startDate`; the list-level `postedOn` is a relative label ("Posted Today"). Up to 5 detail requests run concurrently via `asyncio.Semaphore(5)`. Dedup uses `bulletFields[0]`, the requisition number, since `externalPath` embeds the title and changes on retitling.

**Teamtailor**: the documented REST API (`api.teamtailor.com/v1/jobs`) returns 401 without a per-company token, but every career site also publishes the same postings as an unauthenticated JSON Feed at `{slug}.teamtailor.com/jobs.json`. Each item carries a schema.org `JobPosting` under `_jobposting` with a structured `PostalAddress` (`addressLocality`, `addressCountry` as ISO-2). The feed is unpaginated and complete: `?page=2` returns zero items and the count matches the RSS feed, so soft-deactivation is safe against it. No employment type or department is exposed; `job_type` falls back to the title-derived seniority.

**Rippling**: single GET for the board, no pagination; `hydrate()` fetches `description` (a `{company, role}` pair), `employmentType`, and `createdOn`. `employmentType.label` holds the machine code (`SALARIED_FT`) and `employmentType.id` the human label, the reverse of the usual convention. Locations read `"City, Country"`, so the trailing segment goes through `get_country_code_for_name` when the city is not in the city table. Board slugs are often generic words belonging to unrelated companies (`arc` is the Amyloidosis Research Consortium, `sentry` is Sentry Fire Protection Services), so seed entries take `Company.slug` from the `companyName` in the detail payload.

**YCombinator**: the only ingester that overrides `discover()` with a live directory crawl. The rest inherit the base implementation, which loads `data/companies_{ats_type}.json` when present.

### Planned

| ATS       | Region | Endpoint                                    | Auth         | Blocker                                                  |
| --------- | ------ | ------------------------------------------- | ------------ | -------------------------------------------------------- |
| SEEK      | AU/NZ  | `www.seek.com.au/api/jobsearch/v5/search?siteKey=AU-Main&advertiserid={id}` | None (unofficial) | Endpoint works and filters per advertiser, but sits behind Kasada bot protection and is keyed by numeric advertiser ID |

SEEK is the only candidate that passed a live zero-auth test without being implemented. `GET /api/jobsearch/v5/search?siteKey=AU-Main&advertiserid={id}` returns `advertiser`, `companyName`, `locations[].countryCode`, `classifications`, `listingDate`, `workTypes`, `workArrangements`, and a `teaser`, all of which map onto `Job`. Two things hold it back. The sibling `chalice-search/v4` path returns a Kasada challenge script rather than a 404, so sustained server-side crawling is likely to be blocked and would show up as constant `crawl_error` noise. Boards are also keyed by an opaque numeric advertiser ID with no directory to enumerate, so every company needs a manual lookup. Revisit if a stable per-advertiser entry point appears.

### Not Compatible

| ATS / Platform | Region      | Reason                                                                                                  |
| -------------- | ----------- | ------------------------------------------------------------------------------------------------------- |
| Freshteam      | India       | End of life. Freshworks stops renewals 7 Mar 2026 and sunsets the product Apr 2027. All zero-auth paths confirmed closed: `/api/open_positions` returns 401/403/404 per tenant, `/jobs` serves an HTML SPA, and `freshworks.freshteam.com` itself is 503 |
| iCIMS          | Global      | Career portals are server-rendered HTML with no JSON path and no embedded `JobPosting` JSON-LD; the host pattern also varies per customer (`careers-{slug}` resolved for 1 of 10 tested) |
| Taleo (Oracle) | Global      | `{tenant}.taleo.net` no longer resolves for any of 23 tested tenants; customers have been migrated to Oracle Recruiting Cloud |
| SAP SuccessFactors | Global  | No JSON endpoint. `career{n}.successfactors.*` and `jobs.sap.com` return HTML only; the OData API (`api{n}.sapsf.*`) is auth-gated |
| Bullhorn       | Global      | Public career-portal REST requires a per-customer `corpToken` in the path; unknown tokens return `{"errorMessage":"Bad corp token"}` and there is no directory to resolve them |
| Eightfold AI   | Global      | `{slug}.eightfold.ai/api/apply/v2/jobs` is zero-auth JSON with a usable schema, but only 1 of 9 tested tenants was reachable; the rest return 403 (Cloudflare) or do not resolve, and the subdomain is not derivable from the company name |
| BambooHR       | Global      | `{slug}.bamboohr.com/careers/list` no longer returns JSON. Unknown tenants get the same 43,538-byte marketing page as known ones (verified against a deliberately invalid slug); tenants that do have a board serve an HTML SPA |
| BreezyHR       | USA         | HTTP 403 on all endpoints; auth required                                                                |
| Dice           | USA         | `job-search-api.svc.dhigroupinc.com` returns `{"message":"Missing Authentication Token"}`; the site API path 404s |
| Culinary Agents | USA        | No JSON API; `/api/jobs` 404, `/search/jobs.json` and `/jobs.rss` return HTTP 406                        |
| JazzHR         | USA         | `{slug}.jazz.co/api/jobs` serves SPA, no JSON                                                           |
| Jobvite        | USA         | Auth required                                                                                           |
| Wellfound      | Global      | All API endpoints 403/404; auth required                                                                |
| Welcome to the Jungle | Europe | Algolia-backed search; all `/api/v1/jobs` paths return 404                                            |
| Softgarden     | Europe      | Numeric client IDs required (not human-readable slugs); no per-company API path                         |
| Pinpoint       | Europe      | Auth required on all endpoints                                                                          |
| JOIN.com       | Europe      | v1 deprecated (410); v2 requires `Authorization` header                                                 |
| Personio       | Europe      | XML feed (`{slug}.jobs.personio.de/xml`) works for legacy customers only; newer customers use Personio's Next.js job board builder; aggressive rate limiting |
| Bayt           | Middle East | Cloudflare 403; scraping blocked                                                                        |
| Mihnati        | Middle East | Cloudflare interstitial (403 "Just a moment...") on every path including `/api/*`                       |
| GulfTalent     | Middle East | No public API; Cloudflare-protected                                                                     |
| NaukriGulf     | Middle East | DNS failure; no accessible endpoint                                                                     |
| Talentera      | Middle East | DNS failure; domain unreachable                                                                         |
| Akhtaboot      | Middle East | Elasticsearch API exists but no working per-company filter parameter                                    |
| Wuzzuf         | Middle East | Custom SSR; all `/api/v1/` paths return 404                                                             |
| Darwinbox      | India       | Angular SPA + Cloudflare Turnstile                                                                      |
| Keka HR        | India       | React SPA; no JSON on any `/careers/api/*` path                                                         |
| Instahyre      | India       | No public API                                                                                           |
| Zoho Recruit   | India       | `{slug}.zohorecruit.com/recruit/ats/GetJobs` serves HTML for any slug (including nonexistent ones); `/api/v1/jobs` returns `INVALID_URL_PATTERN`; the v2 API needs OAuth |
| Naukri.com     | India       | `jobapi/v3/search` requires `appid`/`systemid` headers and then returns `{"message":"recaptcha required"}` |
| Hirect         | India       | Domain no longer resolves; product discontinued                                                          |
| JobKorea       | Asia Pacific | HTML SSR only; `/api/Recruit/List` returns 404 and `api.jobkorea.co.kr` times out                        |
| Glints         | SEA         | 403 on all endpoints                                                                                    |
| JobStreet      | SEA         | 403 (MY region); HTML SPA (PH region); Chalice API blocked                                              |
| Computrabajo   | LatAm       | HTTP 403 on both the API path and ordinary listing pages                                                |
| OCC Mundial    | LatAm       | HTTP 403 (`abuse` / Cloudflare interstitial) on all API paths                                           |
| Catho          | LatAm       | HTTP 403 Access Denied (Akamai) on `www` and `api` hosts                                                |
| Bumeran        | LatAm       | HTTP 403 Cloudflare on `/api/avisos/*`                                                                  |
| Gupy           | LatAm       | Career sites are Next.js SSR; no JSON found at `{slug}.gupy.io/api/{job,jobs,v1/jobs}` or on the portal API host |
| Fuzu           | Africa      | Job board; no per-company API                                                                           |
| PNet           | Africa      | No public API                                                                                           |
| MyJobMag       | Africa      | No public API                                                                                           |

## Backlog

Every platform previously listed here has been probed live. Failures are recorded in the Not Compatible table, SEEK in the Planned table. Probe scripts and raw responses live under `ats/`, which is gitignored, matching the earlier per-region research. Two platforms are deferred rather than rejected, because the endpoint works and only the listings are missing:

- **Kalibrr** (PH/ID): `GET www.kalibrr.com/api/companies/{slug}/jobs` is still zero-auth JSON and structurally compatible. Re-probed on the current company set: 4 of 10 slugs resolve, but every one reports `total_count: 0`. Unchanged from the original finding. Revisit if platform activity recovers.
- **NHS Jobs** (UK): `api.jobs.nhs.uk/v1/search` requires a free `Ocp-Apim-Subscription-Key` (Azure APIM, register at `developer.jobs.nhs.uk`); unauthenticated GET and POST both return the APIM gateway page. The RSS paths on `www.jobs.nhs.uk` return HTML, not a feed. The key is static rather than per-company, but the ingestion model is search-based rather than slug-based and needs a different shape from `BaseIngester`. Other healthcare ATS (HealthcareSource, iCIMS, Taleo) require per-organisation auth contracts, and clinical job boards (BioSpace, Health eCareers, Medscape Jobs) have no public JSON API.

Three platforms outside the original backlog were probed alongside it because they fill the same gaps. Rippling passed and is implemented. Eightfold AI and BambooHR failed and are in the Not Compatible table.

## Adding an Ingester

### Standard (zero-auth JSON)

1. Create `backend/app/ingestion/{ats}.py` and subclass `BaseIngester`, set `ats_type`
2. Implement `fetch_raw`, `extract_job_id`, `build_job`
3. If the ATS needs a second request per job, put it in `hydrate()`, not `fetch_raw()`
4. Register in `app/ingestion/__init__.py` under `INGESTERS`
5. Add unit tests in `tests/unit/test_ingesters.py`
6. Update README data sources table and PLAN.md implemented table

### Per-company credential

No implemented ingester needs one. If a future ATS does, it requires a `company.ats_api_key` column (Alembic migration needed), threading the key from `Company` into `ingest()` and `fetch_raw()`, and a registration endpoint or admin script to store keys per company. Teamtailor was the last candidate here and turned out not to need it, so check for an unauthenticated public feed before adding the column.

### Boards addressed by more than a slug

Where one string is not enough to locate a board (Workday needs tenant, data-centre number, and board name), pack the parts into `ats_slug` with `:` separators and parse them in `fetch_raw`. This keeps the existing schema and the `run_ingestion` contract, which passes `company.ats_slug` straight to `ingest()`. Override `_resolve_company` so new stubs still get a readable `Company.slug`; see `workday.py`.

### Discovery

`BaseIngester.discover()` loads `data/companies_{ats_type}.json` when the file exists, so an ATS with no public company directory needs only a seed file. Each entry is `{"name", "slug", "ats_slug"}`, where `ats_slug` defaults to `slug`. Override `discover()` only when the ATS exposes a directory to paginate (YCombinator).

`run_discovery` deduplicates on `Company.slug`, and `_resolve_company` falls back to it when no `ats_slug` matches, so seed slugs must identify the real company. Boards named after generic words are the hazard: on Rippling, `arc` is the Amyloidosis Research Consortium and `sentry` is Sentry Fire Protection Services, and either would attach its jobs to an unrelated existing record. Take the slug from the company name in the payload, not the board address.

Current seed files: `companies_workday.json` (20 boards), `companies_teamtailor.json` (19), `companies_rippling.json` (4). Each was built by probing a candidate list and keeping only boards that returned JSON, so every entry is verified. Rippling's is short because board slugs are not derivable from company names and there is no directory to enumerate; 4 of 39 candidates resolved. To grow a file, re-run the probe scripts under `ats/` with new candidates. No code change is needed.
