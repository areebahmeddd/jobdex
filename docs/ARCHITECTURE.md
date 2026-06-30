# Backend Architecture

## Startup Sequence

On every process start, the lifespan runs three steps in order:

```
1. migrate_db()      apply all pending Alembic migrations to head
2. seed_cities()     upsert cities from data/cities.json into the cities table
3. scheduler.start() register and start all background jobs
```

`seed_cities` is idempotent. It checks for an existing slug before inserting, so it is safe to run on every restart.

## API Endpoints

All endpoints are public with no authentication. Base path: `/`

### Jobs `/jobs`

| Method | Path             | Description                                                    |
| ------ | ---------------- | -------------------------------------------------------------- |
| `GET`  | `/jobs`          | Paginated job list with optional filters and cursor pagination |
| `GET`  | `/jobs/{job_id}` | Full job detail by ID (active jobs only)                       |

Filters: `city`, `country_code`, `region`, `role_category`, `role_subcategory`, `seniority`, `is_remote`, `q` (full-text), `cursor`, `limit`, `offset`

Pagination defaults to offset-based. Pass `cursor` (returned as `next_cursor`) for keyset pagination ordered by `posted_at DESC, id DESC`.

### Companies `/companies`

| Method | Path                     | Description                                  |
| ------ | ------------------------ | -------------------------------------------- |
| `GET`  | `/companies`             | Paginated company list with job counts       |
| `GET`  | `/companies/{slug}`      | Full company profile (active companies only) |
| `GET`  | `/companies/{slug}/jobs` | Paginated jobs for a specific company        |

Filters: `city`, `country_code`, `region`, `industry`, `stage`, `ats_type`, `q` (name/description ILIKE), `limit`, `offset`

### Search `/search`

| Method | Path      | Description                                           |
| ------ | --------- | ----------------------------------------------------- |
| `GET`  | `/search` | Search across jobs and companies in a single response |

Filters: `city`, `role`, `industry`, `country_code`, `region`, `is_remote`, `limit`, `offset`

Response fields: `companies[]`, `jobs[]`, `total_companies`, `total_jobs`.

### Cities `/cities`

| Method | Path             | Description                                          |
| ------ | ---------------- | ---------------------------------------------------- |
| `GET`  | `/cities`        | Paginated city list with live job and company counts |
| `GET`  | `/cities/{slug}` | Single city detail                                   |

Filters: `region`, `country_code`, `limit`, `offset`

### Map `/map`

| Method | Path                            | Description                                                |
| ------ | ------------------------------- | ---------------------------------------------------------- |
| `GET`  | `/map/companies`                | Company pins with coordinates and job counts for the globe |
| `GET`  | `/map/cities`                   | City cluster pins with aggregated job and company counts   |
| `GET`  | `/map/companies/{slug}/offices` | Distinct office locations derived from active jobs         |

Viewport filters: `lat_min`, `lat_max` (range: -90 to 90), `lng_min`, `lng_max` (range: -180 to 180)

Additional filters: `region`, `country_code`, `role`, `is_remote`

`map_companies` resolves display coordinates from the company HQ if set, otherwise falls back to the most common job location by count.

### Stats `/stats`

| Method | Path     | Description                   |
| ------ | -------- | ----------------------------- |
| `GET`  | `/stats` | Aggregate platform statistics |

Response fields: `total_companies` (active), `total_jobs` (all-time), `active_jobs`, `total_cities`, `cities_with_jobs`, `role_categories`, `top_cities`, `top_regions`, `ats_breakdown`.

### Payments `/payments`

| Method | Path                | Description                              |
| ------ | ------------------- | ---------------------------------------- |
| `POST` | `/payments/orders`  | Create a Razorpay order for a donation   |
| `POST` | `/payments/verify`  | Verify Razorpay payment signature        |

Requires `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in the environment. The `key_id` is returned from `/payments/orders` and used by the frontend to initialise Razorpay Checkout. Signature verification uses HMAC-SHA256 over `order_id|payment_id` with `compare_digest` for constant-time comparison.

### Meta

| Method | Path      | Description                         |
| ------ | --------- | ----------------------------------- |
| `GET`  | `/health` | Health check                        |
| `GET`  | `/`       | API metadata and endpoint reference |

## Background Jobs

All jobs run in-process via APScheduler. No separate worker is needed.

| Job ID               | Interval | Function         | Description                                                    |
| -------------------- | -------- | ---------------- | -------------------------------------------------------------- |
| `ingest_all`         | 6 h      | `run_ingestion`  | Crawls all active companies, oldest-first                      |
| `enrich_pending`     | 12 h     | `run_enrichment` | Enriches companies where `enriched_at IS NULL`                 |
| `discover_companies` | 24 h     | `run_discovery`  | Seeds new companies from ingesters that implement `discover()` |

Intervals are configurable via `INGEST_INTERVAL_HOURS`, `ENRICH_INTERVAL_HOURS`, and `DISCOVER_INTERVAL_HOURS`.

## Ingestion Pipeline

Each ATS subclass implements `fetch_raw`, `extract_job_id`, and `build_job`. `BaseIngester` handles dedup, deactivation, geo-lookup, error recording, and the scheduler integration.

Jobs are never hard-deleted. A SHA-256 hash of `ats_type:slug:job_id` is stored as `dedup_hash` on insert. On each crawl, any job whose hash was not seen in the latest response is marked `is_active=False`.

### Flow per company

```
1. _resolve_company()
   Look up company by ats_slug + ats_type.
   Create a stub record if not found.

2. _fetch_company_geo()  [Clearbit autocomplete]
   Populate company HQ: city, country_code, region, lat/lng, logo_url.
   Only runs if company.latitude is not already set.

3. fetch_raw()  [ATS API]
   Call the provider-specific endpoint to get raw job dicts.

4. For each raw job:
   a. extract_job_id()   stable ATS-side ID
   b. make_hash()        SHA-256 of "ats_type:slug:job_id" -> dedup_hash
   c. hash exists        update last_seen_at, set is_active=True
   d. hash is new        build_job() -> normalise -> insert
   e. blocked location   skip silently

5. Deactivate jobs whose dedup_hash was not seen in this crawl.
   Sets is_active=False, last_seen_at=now.

6. _backfill_company_hq()
   If the company still has no city, derive it from the most common
   city across its active jobs.
```

### Normalisation

Raw location strings like `"Bengaluru, KA"`, `"New York, NY (Hybrid)"`, or `"Remote / London"` are resolved to canonical fields by the normaliser.

**Location**: `canonicalize_city` tries alias lookup, exact match, substring match, then fuzzy match via rapidfuzz WRatio (cutoff 90). Falls back to Nominatim if `GEOCODE_UNKNOWN_CITIES` is enabled. Remote and hybrid detection runs via regex on the raw string and is never overwritten by city resolution.

**Role**: title and department matched against `role_patterns.json` to produce `role_category` and `role_subcategory`. Retries against the first 400 chars of description if the title yields no match.

**Seniority**: title matched against `seniority_patterns.json`. Defaults to `mid`.

**Tech stack**: title and description scanned for whole-word matches against `tech_keywords.json`.

```
normalize_location(location_raw)
    canonicalize_city()      exact match, alias, substring, fuzzy (rapidfuzz WRatio >= 90)
    Nominatim geocoder       fallback when GEOCODE_UNKNOWN_CITIES=true
    remote/hybrid detection  regex patterns on the raw location string

classify_role(title, description, department)
    role_category + role_subcategory   matched against role_patterns.json

classify_seniority(title)
    seniority level                    matched against seniority_patterns.json

extract_tech_stack(title, description)
    tech_stack[]                       matched against tech_keywords.json

normalize_job_type(raw_type)
    job_type                           mapped via job_type_map in tech_keywords.json

strip_html() + make_snippet()
    description_snippet                plain text, max 500 chars
```

### ATS providers

**Ashby**: `POST /job-board/jobPostings` with `{jobBoardIdentifier: slug}`. Returns a paginated list. Job ID is the Ashby UUID. Location is sourced from the `locationName` field.

**Greenhouse**: `GET /boards/{slug}/jobs?content=true`. Returns a flat list of job objects with HTML content, location, and department. Job ID is the Greenhouse numeric `id`.

**Lever**: `GET /postings/{slug}?mode=json`. Returns a flat JSON array of postings. Job ID is the Lever UUID. Job type is derived from the `commitment` category field.

**Y Combinator**: `GET /v0.1/companies?q={slug}` on `api.ycombinator.com` (no auth). Since `workatastartup.com` does not expose job listings via a public API, the ingester creates one representative job per hiring company. The job title comes from `oneLiner`, the description from`longDescription`, and the source URL points to the company's Work at a Startup page.`build_job` backfills missing company metadata, and `fetch_raw` returns `[]` when `isHiring` is false to deactivate the job automatically. `is_remote` is set when `regions` contains `"Fully Remote"`.

### Location blocking

Jobs with `country_code = IL` or a city matching `israel`, `tel aviv`, `haifa`, `beer sheva`, or `jerusalem` are skipped at insertion time and never written to the database.

## Enrichment Pipeline

Processes companies where `enriched_at IS NULL`, ordered alphabetically. Once enriched, `enriched_at` is set and the company is skipped on all future runs.

Wikidata provides structured facts: founders, key investors, total funding, funding stage, business model, headcount range, and social profile handles. Wikipedia provides the long-form company description. Social links from Wikidata are merged with any existing `social_links` rather than overwriting them.

All external calls use a shared `httpx.AsyncClient` with `ENRICHMENT_BOT_AGENT` as the User-Agent. `ENRICHMENT_STEP_DELAY` runs between each API call to avoid rate limits.

### Flow per company

```
1. wikidata.search_company()      search by company name to get Wikidata QID
2. wikidata.fetch_company_data()  fetch founders, investors, funding,
                                  social links, business model, headcount
3. wikipedia.fetch_summary()      fetch description from Wikipedia REST API
4. Merge results into Company record
5. Set enriched_at = now
```

## Database

Three tables: `companies`, `jobs`, `cities`. Companies are the root entity. Jobs belong to a company via `company_id`. Cities are a static reference table populated at startup and never written to by ingestion.

### Connection

- Driver: psycopg2 (sync)
- Pool: `pool_size=2`, `max_overflow=3`, `pool_timeout=30s`, `pool_recycle=600s`
- `pool_pre_ping=True`: validates connections before use, required for Neon serverless
- Sessions: context manager via `get_session()` with explicit rollback on exception

### Table: `companies`

One record per company. `ats_type` and `ats_slug` identify which ATS board to crawl. Location fields are populated by Clearbit geo lookup on first ingest or backfilled from the most common job city. Enrichment fields are populated by the enrichment pipeline.

| Column              | Type           | Notes                             |
| ------------------- | -------------- | --------------------------------- |
| `id`                | `String` PK    | UUID v4                           |
| `name`              | `String(255)`  | Required                          |
| `slug`              | `String(255)`  | Unique, indexed                   |
| `logo_url`          | `String(500)`  |                                   |
| `description`       | `Text`         |                                   |
| `website`           | `String(500)`  |                                   |
| `city`              | `String(255)`  | HQ city                           |
| `country`           | `String(255)`  |                                   |
| `country_code`      | `String(2)`    | ISO-2, indexed                    |
| `region`            | `String(50)`   | e.g. `south_asia`                 |
| `latitude`          | `Float`        |                                   |
| `longitude`         | `Float`        |                                   |
| `industry`          | `JSONB`        | Array of industry tags            |
| `stage`             | `String(50)`   | e.g. `series_a`                   |
| `founded_year`      | `Integer`      |                                   |
| `ats_type`          | `String(50)`   | e.g. `ycombinator`                |
| `ats_slug`          | `String(255)`  | ATS board identifier              |
| `last_crawled_at`   | `DateTime(tz)` |                                   |
| `crawl_error`       | `String(500)`  | Last error message                |
| `is_active`         | `Boolean`      |                                   |
| `wikidata_id`       | `String(20)`   | Wikidata QID                      |
| `enriched_at`       | `DateTime(tz)` | Null if not yet enriched          |
| `founders`          | `JSONB`        |                                   |
| `key_investors`     | `JSONB`        |                                   |
| `total_funding_usd` | `BigInteger`   |                                   |
| `funding_stage`     | `String(50)`   |                                   |
| `business_model`    | `String(50)`   |                                   |
| `headcount_range`   | `String(50)`   |                                   |
| `benefits`          | `JSONB`        |                                   |
| `office_address`    | `String(500)`  |                                   |
| `social_links`      | `JSONB`        | Keys: `twitter`, `linkedin`, etc. |

### Table: `jobs`

One record per job posting. `location_raw` preserves the original ATS string. All structured location, role, seniority, and tech fields are produced by the normalisation pipeline. `dedup_hash` is the upsert key. Jobs are soft-deleted by setting `is_active=False`.

| Column                | Type           | Notes                                               |
| --------------------- | -------------- | --------------------------------------------------- |
| `id`                  | `String` PK    | UUID v4                                             |
| `company_id`          | `String` FK    | References `companies.id`                           |
| `title`               | `String(500)`  | Required                                            |
| `description`         | `Text`         | Raw HTML from ATS                                   |
| `description_snippet` | `String(600)`  | Plain text, max 500 chars                           |
| `location_raw`        | `String(500)`  | Original location string from ATS                   |
| `city`                | `String(255)`  | Canonical city name                                 |
| `country`             | `String(255)`  |                                                     |
| `country_code`        | `String(2)`    | ISO-2                                               |
| `region`              | `String(50)`   | e.g. `middle_east`                                  |
| `latitude`            | `Float`        |                                                     |
| `longitude`           | `Float`        |                                                     |
| `is_remote`           | `Boolean`      |                                                     |
| `remote_type`         | `String(50)`   | `remote` or `hybrid`                                |
| `role_category`       | `String(100)`  | e.g. `engineering`, `design`                        |
| `role_subcategory`    | `String(100)`  | e.g. `backend`, `mobile`                            |
| `seniority`           | `String(50)`   | `junior`, `mid`, `senior`, `lead`                   |
| `job_type`            | `String(50)`   | `full_time`, `contract`, etc.                       |
| `department`          | `String(255)`  | Raw department string from ATS                      |
| `tech_stack`          | `JSONB`        | Array of matched tech keywords                      |
| `source_url`          | `String(1000)` | ATS job listing URL                                 |
| `ats_type`            | `String(50)`   |                                                     |
| `ats_job_id`          | `String(255)`  | ATS-side stable job ID                              |
| `dedup_hash`          | `String(64)`   | SHA-256, unique; used for upsert logic              |
| `posted_at`           | `DateTime(tz)` |                                                     |
| `first_seen_at`       | `DateTime(tz)` | Set on first insert                                 |
| `last_seen_at`        | `DateTime(tz)` | Updated on every crawl that sees the job            |
| `is_active`           | `Boolean`      | Set to false when job disappears from the ATS board |

### Table: `cities`

Reference data loaded from `data/cities.json` at startup. Used by the cities and map endpoints. The normaliser reads city metadata from the same JSON file directly, not from this table.

| Column         | Type          | Notes                       |
| -------------- | ------------- | --------------------------- |
| `id`           | `String` PK   | UUID v4                     |
| `name`         | `String(255)` | Canonical city name         |
| `slug`         | `String(255)` | Unique, URL-safe ASCII slug |
| `country`      | `String(255)` |                             |
| `country_code` | `String(2)`   |                             |
| `region`       | `String(50)`  |                             |
| `latitude`     | `Float`       |                             |
| `longitude`    | `Float`       |                             |

### Indexes

Every user-facing job query filters `is_active = TRUE`, so the three composite partial indexes (`city_role`, `region_role`, `country_role`) are preferred over plain single-column indexes. The standalone indexes for `city`, `country_code`, and `role_category` on the jobs table were dropped as redundant in migration `d4e5f6a7b8c9`.

#### companies

| Index                       | Columns              | Type                 |
| --------------------------- | -------------------- | -------------------- |
| `ix_companies_slug`         | `slug`               | Unique               |
| `ix_companies_country_code` | `country_code`       | B-tree               |
| `ix_companies_city_country` | `city, country_code` | B-tree               |
| `ix_companies_region`       | `region`             | B-tree               |
| `ix_companies_industry_gin` | `industry`           | GIN (JSONB contains) |

#### jobs

| Index                         | Columns                                   | Condition          | Purpose                         |
| ----------------------------- | ----------------------------------------- | ------------------ | ------------------------------- |
| `ix_jobs_dedup_hash`          | `dedup_hash`                              |                    | Unique; upsert lookup           |
| `ix_jobs_is_active`           | `is_active`                               |                    | Global active-job count queries |
| `ix_jobs_seniority`           | `seniority`                               |                    | Seniority filter                |
| `ix_jobs_company_active`      | `company_id, is_active`                   |                    | Per-company job queries         |
| `ix_jobs_active_city_role`    | `city, role_category`                     | `is_active = TRUE` | Primary filter for job listings |
| `ix_jobs_active_region_role`  | `region, role_category`                   | `is_active = TRUE` | Region-filtered listings        |
| `ix_jobs_active_country_role` | `country_code, role_category`             | `is_active = TRUE` | Country-filtered listings       |
| `ix_jobs_active_posted`       | `posted_at`                               | `is_active = TRUE` | Sort by recency                 |
| `ix_jobs_active_remote`       | `is_remote`                               | `is_active = TRUE` | Remote-only filter queries      |
| `ix_jobs_fts_gin`             | `tsvector(title, snippet, role_category)` | `is_active = TRUE` | GIN; full-text search           |

#### cities

| Index            | Columns | Type   |
| ---------------- | ------- | ------ |
| `ix_cities_slug` | `slug`  | Unique |

## Caching

Cache headers are set on read-heavy endpoints called repeatedly with identical parameters, such as map pan/zoom, page-load stats, and city reference data. Endpoints driven by user-supplied filter combinations are not cached.

| Endpoint                            | max-age | stale-while-revalidate |
| ----------------------------------- | ------- | ---------------------- |
| `GET /stats`                        | 300s    | 60s                    |
| `GET /cities`                       | 300s    | 60s                    |
| `GET /cities/{slug}`                | 300s    | 60s                    |
| `GET /map/cities`                   | 120s    | 30s                    |
| `GET /map/companies`                | 120s    | 30s                    |
| `GET /map/companies/{slug}/offices` | 120s    | 30s                    |

No CDN is deployed. These headers apply browser-level HTTP caching only.

## Configuration

Settings are loaded from `.env` via `pydantic-settings`. All values have defaults for local development.

| Variable                     | Default                         | Description                                           |
| ---------------------------- | ------------------------------- | ----------------------------------------------------- |
| `DATABASE_URL`               | `postgresql://localhost/jobdex` | PostgreSQL connection string                          |
| `DB_ECHO`                    | `false`                         | Log all SQL statements                                |
| `DB_POOL_SIZE`               | `2`                             | SQLAlchemy pool size                                  |
| `DB_MAX_OVERFLOW`            | `3`                             | Max overflow connections                              |
| `DB_POOL_TIMEOUT`            | `30`                            | Connection acquisition timeout in seconds             |
| `DB_POOL_RECYCLE`            | `600`                           | Connection max lifetime in seconds                    |
| `HTTP_TIMEOUT`               | `30.0`                          | Timeout for ATS HTTP requests                         |
| `CRAWL_DELAY`                | `0.3`                           | Delay between company crawls in seconds               |
| `GEOCODE_UNKNOWN_CITIES`     | `false`                         | Enable Nominatim fallback for unrecognised cities     |
| `GEOCODE_USER_AGENT`         | `JobDex/1.0`                    | User-agent string for Nominatim requests              |
| `ENRICHMENT_BOT_AGENT`       | `JobDex/1.0`                    | User-agent string for Wikidata and Wikipedia requests |
| `ENRICHMENT_REQUEST_TIMEOUT` | `15.0`                          | Timeout for enrichment HTTP requests                  |
| `ENRICHMENT_STEP_DELAY`      | `0.5`                           | Delay between enrichment API calls in seconds         |
| `INGEST_INTERVAL_HOURS`      | `6`                             | Ingestion run interval                                |
| `ENRICH_INTERVAL_HOURS`      | `12`                            | Enrichment job interval                               |
| `DISCOVER_INTERVAL_HOURS`    | `24`                            | Discovery job interval                                |
| `DEBUG`                      | `false`                         | FastAPI debug mode                                    |
