# JobDex Backend — Deep-Dive Q&A

Each question is answered with exact code and file references, cross-checked against the full codebase, and includes a **verdict** on design quality with improvement suggestions where appropriate.

## Bugs & Investigations

## Q1 — Is cron clashing with manual? `[FIXED]`

### What exists

APScheduler registers three jobs in [`backend/app/scheduler.py`](backend/app/scheduler.py):

```python
scheduler.add_job(run_ingestion,  "interval", hours=settings.INGEST_INTERVAL_HOURS,  id="ingest_all",         max_instances=1)
scheduler.add_job(run_enrichment, "interval", hours=settings.ENRICH_INTERVAL_HOURS,  id="enrich_pending",     max_instances=1)
scheduler.add_job(run_discovery,  "interval", hours=settings.DISCOVER_INTERVAL_HOURS,id="discover_companies", max_instances=1)
```

The manual scripts (`scripts/ingest.py`, `scripts/discover.py`, `scripts/enrich.py`) call the exact same functions (`run_ingestion`, `run_discovery`, `run_enrichment`). `max_instances=1` only prevents the APScheduler trigger from firing the same job twice concurrently — it has no effect on the manual script process.

### The actual risk

If you run `python scripts/ingest.py --all` while the scheduler's `ingest_all` is mid-run:

1. Both processes independently load the same company list from the DB.
2. Both call `ingest(ats_slug, db)` for the same company.
3. Both execute `fetch_raw` against the ATS — **double HTTP traffic** to the ATS.
4. Both walk the same raw jobs and try to `db.add(job)`.
5. The `dedup_hash` unique constraint on the `jobs` table catches duplicate inserts and raises `IntegrityError`.
6. That `IntegrityError` is caught by the bare `except Exception` in the per-job loop in `base.py` and silently counted as an error.

```python
# backend/app/ingestion/base.py
except Exception as exc:  # noqa: BLE001
    msg = f"Error on job id={raw.get('id', '?')}: {exc}"
    logger.warning(msg)
    result.errors.append(msg)
```

So it won't crash, but you'll see spurious error counts in logs and the `company.crawl_error` might get set from the outer exception path.

### Verdict

**Minor real risk.** The unique constraint acts as a last-resort guard so data won't be corrupted, but you'll get noisy errors and double ATS load. For the current scale (single process, manual scripts run rarely) this is acceptable. It becomes a genuine problem if you ever run multiple replicas or automate scripts on a schedule outside APScheduler.

### Suggested fix (minimal, balanced)

Add a lightweight advisory lock or a DB-backed flag:

```python
# In run_ingestion(), after fetching targets:
if scheduler.get_job("ingest_all") and scheduler.get_job("ingest_all").next_run_time:
    # Check a "running" sentinel in a config/locks table, or just log a warning
    pass
```

Or more practically: document that scripts should not be run while the server is up, and add a `--force` flag guard to the scripts. A full distributed lock (Redis `SET NX`, Postgres advisory lock) is only needed if you add multiple server replicas.

## Q3 — What happens if cron runs and finds the same data? `[FIXED]`

### The exact flow

From [`backend/app/ingestion/base.py`](backend/app/ingestion/base.py):

```python
active_hashes: set[str] = {row.dedup_hash for row in existing_rows if row.is_active}
seen_hashes: set[str] = set()

for raw in raw_jobs:
    job_id = self.extract_job_id(raw)
    dedup_hash = self.make_hash(slug, job_id)
    seen_hashes.add(dedup_hash)

    if dedup_hash in existing_hash_to_id:
        db.query(Job).filter(Job.id == existing_hash_to_id[dedup_hash]).update(
            {"last_seen_at": now, "is_active": True},
            synchronize_session=False,
        )
        result.updated_jobs += 1
    else:
        # new job — insert
        ...

expired = active_hashes - seen_hashes
if expired:
    db.query(Job).filter(Job.dedup_hash.in_(expired)).update(
        {"is_active": False}, synchronize_session=False
    )
```

So for **identical data**:

- Every existing job gets an `UPDATE SET last_seen_at = now, is_active = true` — O(n) updates per crawl, even when nothing changed.
- `result.updated_jobs` is incremented for each.
- No new inserts happen.
- No deactivations happen (expired = empty set).

This is a **heartbeat** pattern: `last_seen_at` acts as a liveness timestamp. If the ATS stops returning a job, `last_seen_at` stops updating and `expired` eventually marks it inactive.

### The actual "skip?" question

There is **no skip**. Every job seen in the ATS response always triggers an `UPDATE`, even if nothing changed. This is by design to keep `last_seen_at` current. The trade-off is N UPDATE statements per crawl for N jobs, even on unchanged data.

### Verdict

**Correct and deliberate.** The heartbeat approach is clean and simple for this scale. The cost is N writes per run per company — for 200 jobs, that's 200 indexed UPDATE statements, which Postgres handles trivially.

**Potential improvement for scale:** Add a condition to the UPDATE to skip if `last_seen_at` was already set today:

```python
db.query(Job).filter(
    Job.id == existing_hash_to_id[dedup_hash],
    Job.last_seen_at < today_start,  # only update if stale
).update({"last_seen_at": now, "is_active": True}, synchronize_session=False)
```

This halves write pressure when re-running within the same day, but adds complexity. At current scale it's not needed.

## Q4 — Error handling? `[FIXED]`

### Layer 1 — Per-job parse errors (base.py)

```python
# backend/app/ingestion/base.py
for raw in raw_jobs:
    try:
        job_id = self.extract_job_id(raw)
        ...
        job = self.build_job(raw, company, slug)
        ...
    except Exception as exc:  # noqa: BLE001
        msg = f"Error on job id={raw.get('id', '?')}: {exc}"
        logger.warning(msg)
        result.errors.append(msg)
```

Catches everything — parse failures, missing fields, bad data. Loop continues, error is appended to `IngestResponse.errors`. **Good: one bad job doesn't kill the whole company crawl.**

### Layer 2 — HTTP errors (base.py)

```python
except httpx.HTTPStatusError as exc:
    msg = f"HTTP {exc.response.status_code} from {self.ats_type} board '{slug}'"
    logger.error(msg)
    result.errors.append(msg)
    company.crawl_error = msg
    db.commit()
    return result
except httpx.RequestError as exc:
    msg = f"Network error from {self.ats_type} board '{slug}': {exc}"
    logger.error(msg)
    company.crawl_error = msg
    db.commit()
    return result
```

Differentiates HTTP status errors (4xx/5xx) from network errors (timeout, DNS). Stores the last error on the company record. **Good distinction.** However `crawl_error` is never exposed via the API, so there's no operational visibility without querying the DB directly.

### Layer 3 — Per-company errors (scheduler.py)

```python
# backend/app/scheduler.py
try:
    with get_session() as db:
        result = await ingester.ingest(ats_slug, db)
    total_new += result.new_jobs
    ...
except Exception as exc:
    logger.warning(f"[scheduler] ingest failed for {slug}: {exc}")
    errors += 1
```

If `ingest()` raises (beyond the HTTP error handlers, e.g. a DB error), the scheduler catches it, logs a warning, and moves to the next company. **One bad company doesn't stop the entire run.**

### Layer 4 — Session rollback (database.py)

```python
# backend/app/database.py
@contextmanager
def get_session():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

Any unhandled exception inside a `with get_session()` block rolls back the transaction. **Correct and clean.**

### What's missing / problems

1. **No retry logic.** A transient 503 from an ATS API is treated as a permanent failure until the next cron run (6 hours). A simple exponential backoff would dramatically improve reliability.
2. **No circuit breaker.** If an ATS API is down for days, every cron run still tries every company on that ATS and collects errors. A per-ATS failure count with skip logic would reduce noise.
3. **`crawl_error` is invisible.** The field is written but not surfaced. A `/companies?has_errors=true` filter or a `/admin/errors` endpoint would help ops.
4. **`noqa: BLE001` (blind exception)**. Catching all exceptions in the per-job loop hides programmer errors (e.g., AttributeError in `build_job`) alongside data errors. Narrowing to `(KeyError, ValueError, TypeError)` would be safer.
5. **Discovery uses `logger.error` for failures, ingestion uses `logger.warning`** — this inconsistency makes log-level-based alerting unreliable.

## Q10 — Are the time intervals logically correct? `[FIXED]`

From [`backend/app/config.py`](backend/app/config.py):

```python
INGEST_INTERVAL_HOURS: int = 6
ENRICH_INTERVAL_HOURS: int = 12
DISCOVER_INTERVAL_HOURS: int = 24
```

And the delays:

```python
CRAWL_DELAY: float = 0.3           # Between companies in ingestion
ENRICHMENT_STEP_DELAY: float = 0.5  # Between API calls in enrichment
```

### Analysis per interval

**Ingest: 6h ✓**
Job boards don't refresh faster than a few hours in practice. 6h means you're at most 6h stale. Reasonable for a discovery/index product (vs. a realtime job alerts service). The `order_by(last_crawled_at.asc().nullsfirst())` ensures new companies get crawled immediately on the next cycle.

**Enrich: 12h ⚠**
The enrichment job filters `enriched_at IS NULL`. After all companies are enriched (say, after week 2), this job runs every 12h but processes **zero companies** every time. It's a perpetual no-op after the initial catchup. The log output will be `enriched=0 errors=0` twice daily forever. This is harmless but wastes a scheduler slot.

More importantly: **company data changes over time** (new funding rounds, headcount changes, social links). The current model never re-enriches. A company that closed a Series B last week won't get its `funding_stage` updated unless `enriched_at` is manually reset.

**Discover: 24h ✓**
New companies don't appear on YC's hiring list that frequently. 24h is appropriate. Discovery is idempotent (slug check before insert), so running it more often would just increase the `skipped` count.

**CRAWL_DELAY: 0.3s ✓ (for now)**
0.3s between companies is polite to the ATS APIs. However, this is a global delay — if you have 50 Greenhouse companies back-to-back, you're hammering `boards-api.greenhouse.io` with requests 0.3s apart. A per-ATS delay or a per-domain rate limiter would be more respectful.

**ENRICHMENT_STEP_DELAY: 0.5s ✓**
0.5s between Wikidata and Wikipedia calls is appropriate given their rate-limit policies.

### Verdict

**Intervals are broadly correct.** The logical bug is the enrichment scheduler becoming a permanent no-op. Fix:

```python
# Option A: Change filter to re-enrich older than N days
.filter(
    Company.is_active.is_(True),
    or_(
        Company.enriched_at.is_(None),
        Company.enriched_at < (datetime.now(UTC) - timedelta(days=90))
    )
)
```

Or:

```python
# Option B: Run enrichment once on startup then stop the job
scheduler.add_job(run_enrichment, "interval", hours=12, id="enrich_pending", max_instances=1)
# And add a check in run_enrichment: if no pending, remove the job
```

Option A is the better production choice as it keeps company data reasonably fresh.

## Architecture & Design

## Q2 — Is DB data deduplicated or repeated?

### The dedup mechanism

In [`backend/app/models.py`](backend/app/models.py):

```python
dedup_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
```

This is a database-level `UNIQUE` constraint (Alembic generates it from `unique=True`) — not just an application-level check.

The hash is computed in [`backend/app/ingestion/base.py`](backend/app/ingestion/base.py):

```python
def make_hash(self, slug: str, job_id: str) -> str:
    return hashlib.sha256(f"{self.ats_type}:{slug}:{job_id}".encode()).hexdigest()
```

So `dedup_hash = SHA-256("greenhouse:airbnb:12345")`. All three components (ATS type, company slug, job ID) are embedded, making it globally unique across ATS providers.

### What happens on each crawl

```python
# backend/app/ingestion/base.py
existing_rows = (
    db.query(Job.dedup_hash, Job.id, Job.is_active)
    .filter(Job.company_id == company.id, Job.dedup_hash.isnot(None))
    .all()
)
existing_hash_to_id: dict[str, str] = {row.dedup_hash: row.id for row in existing_rows}
```

The ingester loads all existing hashes for the company **before** the loop. New hashes → INSERT; known hashes → UPDATE `last_seen_at` only. This means for a company with 200 jobs that are all unchanged, you get 200 `UPDATE` statements touching only a timestamp — no duplicates inserted.

### Potential duplication gap

Company records can be duplicated if `_resolve_company` creates a stub using `slug` that doesn't match `ats_slug`:

```python
# backend/app/ingestion/base.py
company = db.query(Company).filter(Company.ats_slug == slug, Company.ats_type == self.ats_type).first()
if company is None:
    company = db.query(Company).filter(Company.slug == slug).first()
if company is None:
    company = Company(name=..., slug=slug, ats_type=..., ats_slug=slug)
```

If the same real-world company was discovered under slug `"acme-corp"` by YC (with `ats_type="ycombinator"`) and later ingested via Greenhouse (with `slug="acme"`, `ats_type="greenhouse"`), they'd create two separate Company rows. The `Company.slug` unique constraint would only prevent exact slug collisions. **Cross-ATS deduplication at the company level does not exist.**

### Verdict

**Job-level deduplication is solid and DB-enforced.** Company-level cross-ATS deduplication is absent by design — each ATS provider has its own slug namespace. For the current scope (one ATS per company) this is fine. If you ever onboard a company on multiple ATS types, a manual merge or canonical-company concept would be needed.

## Q5 — How is pagination happening? Offset vs cursor?

### Jobs endpoint — Hybrid

[`backend/app/routers/jobs.py`](backend/app/routers/jobs.py) implements both modes simultaneously:

**Cursor (keyset) pagination:**

```python
def _encode_cursor(posted_at: datetime | None, job_id: str) -> str:
    payload = {"p": posted_at.isoformat() if posted_at else "", "i": job_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

# In the route:
if cursor:
    decoded = _decode_cursor(cursor)
    if decoded:
        cursor_posted_at, cursor_id = decoded
        query = query.filter(
            or_(
                Job.posted_at < cursor_posted_at,
                and_(Job.posted_at == cursor_posted_at, Job.id < cursor_id),
            )
        )
    rows = query.order_by(Job.posted_at.desc().nullslast(), Job.id.desc()).limit(limit).all()
    total = None  # not computed for cursor pages
```

**Offset pagination:**

```python
else:
    total = query.count()
    rows = query.order_by(Job.posted_at.desc().nullslast(), Job.id.desc()).offset(offset).limit(limit).all()
```

The cursor is a Base64-encoded JSON of `{p: posted_at_iso, i: job_id}`. It handles `NULL posted_at` by treating it as the lowest value (pushed to the end via `nullslast`).

**Other endpoints (companies, cities, search):** Offset only.

### Problems

1. **`total = None` when using cursor** — the response schema allows `total: int | None`, which is correct but the client gets no indication of the full dataset size on cursor pages. Standard for keyset but worth documenting.
2. **Both `cursor` and `offset` can be passed simultaneously.** When `cursor` is present, `offset` is ignored entirely but still accepted without error. The response returns `offset: None` in cursor mode, which could confuse a client that passed `offset=40`.
3. **No stable sort guarantee for offset mode.** If new jobs are inserted between page 1 and page 2 fetches (offset=0 and offset=20), the page 2 result will be shifted, causing duplicates or skipped rows. The cursor mode solves this; the offset mode doesn't.
4. **Search endpoint runs 3 separate queries**: `query.count()` for total jobs, `query.with_entities(func.count(func.distinct(Job.company_id)))` for total companies, then the paged `.offset().limit()`. These are three round trips without a transaction wrapping them — counts could be inconsistent with the page result.
5. **`limit` upper bound is 100** for jobs/companies, but 200 for cities. Inconsistency.

### Verdict

Cursor pagination on jobs is well-implemented and uses the right indexed columns (`ix_jobs_active_posted`). The hybrid approach is pragmatic. The search endpoint's triple-query pattern is a performance smell at scale.

## Q6 — Are there safe checks before insertion or on startup?

### Startup sequence

[`backend/app/main.py`](backend/app/main.py):

```python
async def lifespan(app: FastAPI):
    migrate_db()   # 1. Alembic upgrade head
    seed_cities()  # 2. Upsert cities from cities.json
    _scheduler.start()  # 3. Start background jobs
```

**`migrate_db()`** runs `alembic upgrade head` on every startup:

```python
# backend/app/database.py
def migrate_db() -> None:
    from alembic.config import Config
    from alembic import command
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    command.upgrade(cfg, "head")
```

This is safe. If migrations are already at head, Alembic is a no-op. **Good practice.**

**`seed_cities()`** has an existence check per city:

```python
# backend/app/startup.py
if not db.query(City).filter(City.slug == slug).first():
    db.add(City(...))
```

Idempotent but uses an **N+1 pattern** — one SELECT per city in `cities.json`. If you have 500 cities, that's 500 individual SELECT queries before the batch INSERT. At startup this is a minor cost, but it's worth noting.

### Before insertion checks

**Company resolution (`_resolve_company`):**

```python
# backend/app/ingestion/base.py
company = db.query(Company).filter(Company.ats_slug == slug, Company.ats_type == self.ats_type).first()
if company is None:
    company = db.query(Company).filter(Company.slug == slug).first()
if company is None:
    company = Company(...)
    db.add(company)
    db.flush()
```

Two-stage lookup before creating a stub. Safe.

**Job deduplication:**

```python
existing_hash_to_id: dict[str, str] = {row.dedup_hash: row.id for row in existing_rows}
```

Pre-flight hash map built from DB before the insert loop. Backed by a DB-level unique constraint as last resort.

**Location blocking:**

```python
if is_blocked_location(job.country_code, job.city):
    logger.info(f"[{self.ats_type}] '{slug}' skipping blocked location: {job.city}, {job.country_code}")
    seen_hashes.discard(dedup_hash)
    continue
```

Checked after `build_job()` but before `db.add(job)`. Note: `seen_hashes.discard(dedup_hash)` is important — it prevents previously-active blocked jobs from being deactivated incorrectly.

**Geo-fetch guard:**

```python
if not company.latitude:
    geo = await _fetch_company_geo(company.name)
```

Only calls Clearbit if `latitude` is not set. Prevents re-fetching on every crawl. **Good.**

### What's missing

1. **`seed_cities()` N+1:** Should bulk-load existing slugs first then do a set-difference:

   ```python
   existing_slugs = {r.slug for r in db.query(City.slug).all()}
   new_cities = [City(...) for name, info in city_data.items() if _slugify(name) not in existing_slugs]
   db.bulk_save_objects(new_cities)
   ```

2. **No schema validation of ATS responses.** `fetch_raw()` returns raw dicts and `build_job()` uses `.get()` with defaults everywhere — fine for resilience, but a missing required field like `raw["id"]` (used in `extract_job_id`) will raise a `KeyError` that gets caught by the bare except. A Pydantic model for the raw ATS response would provide better error messages.
3. **No health check for DB connection before scheduler starts.** If the DB is briefly unavailable at startup, `migrate_db()` raises and the app crashes. This is actually fine (fail-fast is correct), but there's no retry.

## Q7 — What happens with 10+ ATS? Is Kafka/queue needed?

### Current architecture

[`backend/app/scheduler.py`](backend/app/scheduler.py):

```python
async def run_ingestion() -> None:
    with get_session() as db:
        targets = [
            (company.ats_type, company.ats_slug, company.slug)
            for company in db.query(Company)
            .filter(Company.is_active.is_(True), Company.ats_type.isnot(None))
            .order_by(Company.last_crawled_at.asc().nullsfirst())
            .all()
        ]

    for ats_type, ats_slug, slug in targets:
        ingester = INGESTERS.get(ats_type)
        ...
        result = await ingester.ingest(ats_slug, db)
        ...
        await asyncio.sleep(settings.CRAWL_DELAY)  # 0.3s
```

This is **fully sequential**: one company at a time, 0.3s delay between each. Even though this is `async`, there's no concurrency — each `ingest()` is `await`ed to completion before the next starts.

### Time math

For N companies with average ATS latency of 1s and `CRAWL_DELAY=0.3s`:

- 50 companies → ~65 seconds per run ✓
- 200 companies → ~4.3 minutes per run ✓
- 500 companies → ~10.8 minutes per run (within 6h window) ✓
- 5000 companies → ~1.8 hours per run (still within 6h window, barely) ⚠
- 20,000 companies → ~7.2 hours — **exceeds the 6h interval** ✗

### The 4 ATS providers issue

All 4 ingesters are registered in `INGESTERS`. `run_ingestion` processes them all sequentially based on `last_crawled_at`, regardless of which ATS they belong to. So having 10 ATS types doesn't change the sequential model — you'd just have more total companies.

### Kafka/queue needed?

**Not at current scale.** For hundreds of companies across 4-10 ATS types, the sequential async model is fine. The `order_by(last_crawled_at.asc().nullsfirst())` ensures no company is permanently starved.

**Where it breaks down:**

- If you scale to thousands of companies and need results fresher than 6h
- If ATS APIs become rate-limited (currently no per-ATS rate limiting is implemented — all companies on the same ATS will hit it in rapid succession)
- If you need parallel processing across multiple server instances

### Realistic improvement path

**Step 1 (current scale):** Add per-ATS concurrency with `asyncio.Semaphore`:

```python
sem = asyncio.Semaphore(3)  # 3 concurrent requests per ATS

async def ingest_with_sem(ingester, slug, sem):
    async with sem:
        async with get_session() as db:
            return await ingester.ingest(slug, db)

tasks = [ingest_with_sem(INGESTERS[ats_type], slug, sem) for ats_type, slug, _ in targets]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Step 2 (at scale):** Move to a task queue (Celery + Redis or ARQ) — but this adds significant operational complexity. Only justified at 1000+ companies.

**Kafka is overkill** for this use case. It's designed for high-throughput event streaming, not scheduled polling of 4 ATS APIs.

## Q8 — What is ingestion doing vs discover vs enrich?

These three pipelines are completely separate and serve different purposes:

### Discovery (`run_discovery` → `ingester.discover()`)

**What:** Seeds the DB with new **Company** records.

**When:** Every 24h, or manually via `python scripts/discover.py`.

**How:**

```python
# backend/app/scheduler.py
for ats_name, ingester in INGESTERS.items():
    stubs = await ingester.discover()
    for stub in stubs:
        existing = db.query(Company).filter(Company.slug == stub.slug).first()
        if existing:
            skipped += 1
            continue
        db.add(stub)
        db.commit()
        added += 1
```

Only **YCombinator** implements `discover()` meaningfully — it paginates `api.ycombinator.com/v0.1/companies?isHiring=true` to get all hiring companies. Ashby, Greenhouse, Lever return an empty list (no bulk-discovery API exists for them). Companies manually added to the DB or via the probe/discover scripts also become discoverable.

**Output:** Company stub records with basic info (name, slug, location, ATS metadata). No jobs yet.

### Ingestion (`run_ingestion` → `ingester.ingest()`)

**What:** Fetches actual **Job** listings for known companies.

**When:** Every 6h, or manually via `python scripts/ingest.py`.

**How:** For each active company with an `ats_type`:

1. Calls the ATS API to get current job listings
2. Normalizes location, role, seniority, tech stack
3. Upserts jobs using `dedup_hash`
4. Deactivates jobs no longer in the ATS response
5. Updates `company.last_crawled_at`

**Output:** Job records, company location data, `last_crawled_at` timestamp.

### Enrichment (`run_enrichment` → `enrich_company()`)

**What:** Adds structured metadata to **Company** records from Wikidata + Wikipedia.

**When:** Every 12h (but only processes companies where `enriched_at IS NULL` — so effectively one-time per company).

**How:**

```python
# backend/app/enrichment/runner.py
qid = await wikidata.search_company(client, company.name)
wd = await wikidata.fetch_company_data(client, qid)
about = await wikipedia.find_summary(client, company.name, wikidata_qid=qid)
# Merges: founders, investors, social links, headcount, founded_year, description
company.enriched_at = datetime.now(UTC)
db.commit()
```

**Output:** Company fields filled: `description`, `founded_year`, `founders`, `social_links`, `headcount_range`, `industry`, `wikidata_id`, `enriched_at`.

### The intended flow

```
Discovery (24h)
  → Creates Company stubs from YC hiring list

Ingestion (6h)
  → Fetches jobs for each known Company
  → Backfills Company HQ from job locations (Clearbit or job-derived)

Enrichment (12h, one-time)
  → Adds deep metadata to Company records from Wikidata/Wikipedia
```

Discovery and Enrichment are about **companies**. Ingestion is about **jobs**. They are independent and can run in any order.

## Q9 — Are all relevant places logging, or did we overdo it?

### What's logged

| Location | Level | What |
|---|---|---|
| `main.py` lifespan | `info` | App start/stop, version |
| `scheduler.py` | `info` | Each run start, final summary (new/updated/errors) |
| `scheduler.py` | `warning` | Per-company ingest failure |
| `scheduler.py` | `error` | Per-ATS discovery failure |
| `ingestion/base.py` | `info` | Company created, raw jobs count, deactivation count, done summary |
| `ingestion/base.py` | `debug` | Geocode success |
| `ingestion/base.py` | `error` | HTTP status and network errors |
| `ingestion/base.py` | `warning` | Per-job parse error |
| `ingestion/base.py` | `info` | Blocked location skip |
| `startup.py` | `info` | City seed count |
| `enrichment/runner.py` | `info` | Start, no Wikidata found, done with field count |
| `database.py` | `info` | Migrations applied |

### Assessment

**Generally well-calibrated.** The key events are logged at appropriate levels:

- Scheduler summaries at `info` are useful for monitoring
- HTTP errors at `error` will trigger alerts in most log aggregators
- Per-job parse failures at `warning` won't flood production logs under normal conditions
- Geocoding at `debug` is correctly noisy-but-suppressable

**Overlogged:**

- `logger.info(f"[{self.ats_type}] '{slug}' -> {len(raw_jobs)} raw jobs")` + `logger.info(f"[{self.ats_type}] '{slug}' done - ...")` — two info lines per company. For 200 companies, that's 400 info lines per ingestion run. This is fine for development but noisy in production without log filtering.
- `logger.info` for blocked location skips — these could be `debug` since they're expected and frequent.

**Underlogged:**

- No request ID / correlation ID — can't trace a specific company through scheduler → ingestion → DB in a log aggregator
- `crawl_error` is never logged to a monitoring channel — you can't alert on companies with persistent crawl errors
- No timing logs (how long did ingesting company X take?)
- No log on enrichment when `enriched_at` is already set (scheduler just skips silently)
- Router endpoints have zero logging — no way to audit what queries are hitting the DB

**Not over-engineered:** No unnecessary trace/span logging. `DEBUG` is used sparingly. No structured JSON logging is set up (Loguru is text-format by default), but adding that would be a one-liner change to the Loguru config.

## Q11 — Are operations idempotent and atomic?

### Idempotency analysis

| Operation | Idempotent? | Mechanism |
|---|---|---|
| `seed_cities()` | ✓ Full | Slug existence check before insert |
| `run_discovery()` | ✓ Full | Slug existence check before insert |
| `run_ingestion()` | ✓ Effective | Dedup hash + unique constraint; UPDATEs are idempotent (same values) |
| `run_enrichment()` | ✓ Partial | `enriched_at IS NULL` filter; re-running for same company writes same data |
| Job deactivation | ✓ Full | `UPDATE is_active=False` on same set is idempotent |

**Discovery batching (single session per ATS):**

```python
# backend/app/scheduler.py
stub_slugs = [s.slug for s in stubs]
with get_session() as db:
    existing_slugs = {
        row.slug
        for row in db.query(Company.slug).filter(Company.slug.in_(stub_slugs)).all()
    }
    new_stubs = [s for s in stubs if s.slug not in existing_slugs]
    for stub in new_stubs:
        db.add(stub)
    db.commit()
added += len(new_stubs)
skipped += len(stubs) - len(new_stubs)
```

The slug check and all inserts for one ATS happen inside a **single session**. The `IN` query fetches all existing slugs at once, new stubs are filtered in Python, and the entire batch is committed atomically. A theoretical race remains (another process inserting a slug between the `IN` query and `db.commit()`), but it is now a narrow window across a single batch commit rather than two separate sessions per company.

### Atomicity analysis

**Per-company ingestion:**

```python
# backend/app/scheduler.py
with get_session() as db:
    result = await ingester.ingest(ats_slug, db)
```

The entire ingest for one company (all job inserts + updates + deactivations + company update + `db.commit()`) happens within a single `get_session()` context. If anything fails before `db.commit()`, the `except Exception: db.rollback()` in `get_session()` rolls back all changes for that company atomically. **Correct.**

**Per-company enrichment:**

```python
# backend/app/scheduler.py
with get_session() as db:
    await enrich_company(slug, db)
```

Same pattern — atomic per company. If the Wikidata SPARQL call succeeds but Wikipedia fails, the already-fetched Wikidata fields won't be committed (good). However, `db.commit()` is called inside `enrich_company` itself:

```python
# backend/app/enrichment/runner.py
company.enriched_at = datetime.now(UTC)
db.commit()
db.refresh(company)
```

This means the session is committed inside the function, not by the caller. If you add logic after `await enrich_company(slug, db)` that needs to be in the same transaction, it can't be. Minor architecture concern for future extensibility.

**Seed cities:**

```python
# backend/app/startup.py
with get_session() as db:
    added = 0
    for name, info in city_data.items():
        if not db.query(City).filter(City.slug == slug).first():
            db.add(City(...))
            added += 1
    db.commit()
```

All cities are inserted in a single transaction. If one fails (e.g., an ORM error), all are rolled back. Correct.

### Race condition in discovery

Discovery narrows the check-then-act window by batching all inserts for one ATS into a single session (see the batching note above). A concurrent process inserting the same slug between the `IN` check and `db.commit()` would produce an `IntegrityError` on the unique `slug` constraint, which would roll back the entire batch for that ATS and be logged by the outer `try/except`. For further hardening, the insert could use `INSERT ... ON CONFLICT DO NOTHING` via `sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_nothing()`.

## Q12 — How is searching and DB ops working?

### Full-text search (`/jobs?q=`)

```python
# backend/app/routers/jobs.py
if q:
    query = query.filter(
        text(
            "to_tsvector('english',"
            " coalesce(jobs.title,'') || ' ' ||"
            " coalesce(jobs.description_snippet,'') || ' ' ||"
            " coalesce(jobs.role_category,''))"
            " @@ websearch_to_tsquery('english', :q)"
        ).bindparams(q=q)
    )
```

This uses PostgreSQL's native FTS with `websearch_to_tsquery` (supports quoted phrases, `AND`, `OR`, `-` negation). The GIN index defined in the model:

```python
# backend/app/models.py
Index(
    "ix_jobs_fts_gin",
    text("to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description_snippet,'') || ' ' || coalesce(role_category,''))"),
    postgresql_using="gin",
    postgresql_where=text("is_active = TRUE"),
)
```

**This index is a partial index** (only active jobs) matching the query filter. However, the `to_tsvector` in the query must be **exactly identical** to the one in the index definition for PostgreSQL to use the index. They are currently identical, so the FTS index will be used. ✓

### Search endpoint (`/search`) — structural inefficiency

```python
# backend/app/routers/search.py
total_jobs = query.count()
total_companies_count = (
    query.with_entities(func.count(func.distinct(Job.company_id))).scalar() or 0
)
paged_rows = query.order_by(Job.posted_at.desc()).offset(offset).limit(limit).all()
```

Three separate DB round trips for the same query with different projections. On a large dataset with complex filters, this is expensive. Can be collapsed to two trips using a window function or a CTE — but for the current scale it's fine.

### Filter pattern — industry JSONB search

```python
# backend/app/routers/companies.py
if industry:
    base = base.filter(Company.industry.cast(JSONB).contains([industry.lower()]))
```

`Company.industry` is already of type `JSONB` in the ORM (`Mapped[list[str] | None] = mapped_column(JSONB)`), so `.cast(JSONB)` is redundant but harmless. The `contains([industry.lower()])` translates to `industry @> '["fintech"]'::jsonb`, which uses the GIN index:

```python
Index("ix_companies_industry_gin", "industry", postgresql_using="gin"),
```

✓ This is correct and efficient.

### Map endpoint — complex subquery chaining

```python
# backend/app/routers/map.py
# Subquery 1: count jobs per (company, lat, lng) combination
loc_counts = loc_counts_q.group_by(...).subquery("loc_counts")

# Subquery 2: pick the best (most common) location per company
best_loc = db.query(loc_counts.c.company_id, ...).distinct(loc_counts.c.company_id).order_by(
    loc_counts.c.company_id, loc_counts.c.loc_cnt.desc()
).subquery("best_loc")

# Main query: resolve company coordinates with fallback to job locations
resolved_lat = func.coalesce(Company.latitude, best_loc.c.latitude)
```

This uses `DISTINCT ON (company_id) ORDER BY company_id, loc_cnt DESC` — a PostgreSQL-specific pattern that picks the row with the highest `loc_cnt` per company. It's correct and efficient. However this query has no pagination — it returns **all** companies with coordinates in one shot. For the map use case this is intentional (the front-end handles clustering), but it's worth noting this could return thousands of rows.

### DB connection pool

```python
# backend/app/config.py
DB_POOL_SIZE: int = 2
DB_MAX_OVERFLOW: int = 3
```

Max 5 simultaneous connections. For a single-process API this is adequate since each request holds a connection only for the duration of one route handler. Under concurrent load (e.g., 20 simultaneous requests), requests beyond the 5th will wait up to `DB_POOL_TIMEOUT=30s`. This is the tightest resource constraint in the system.

### Index coverage summary

| Filter | Index used |
|---|---|
| `is_active = TRUE` | All partial indexes |
| `city + role_category` | `ix_jobs_active_city_role` |
| `region + role_category` | `ix_jobs_active_region_role` |
| `country_code + role_category` | `ix_jobs_active_country_role` |
| `is_remote` | `ix_jobs_active_remote` |
| FTS (`q=`) | `ix_jobs_fts_gin` |
| `posted_at` (sort/cursor) | `ix_jobs_active_posted` |
| `company_id + is_active` | `ix_jobs_company_active` |
| `companies.slug` | built-in unique index |
| `companies.industry` JSONB | `ix_companies_industry_gin` |
| `companies.city + country_code` | `ix_companies_city_country` |

Coverage is comprehensive. Notable gaps:

- **`Job.seniority`** has a simple index (`index=True`) but no partial index on `is_active=TRUE`, so `seniority` filters scan all jobs including inactive ones before the `is_active` filter is applied — minor inefficiency.
- **Combined filters** like `city + seniority` or `role + is_remote` have no composite partial index. PostgreSQL will use bitmap AND across the relevant partial indexes, which is usually fine.

### Overall DB ops quality

The ORM usage is clean and correct. `synchronize_session=False` on bulk UPDATEs is correctly used (the session is committed after and the objects aren't accessed again). `db.flush()` before `_backfill_company_hq` is correct (ensures the company ID is available for the sub-query). Relationships use `lazy="select"` (explicit N+1 avoidance is handled by manually joining in queries rather than relying on relationship loading).

## Summary Table

| # | Question | Status | Severity |
|---|---|---|---|
| 1 | Cron vs manual clash | Minor race, guarded by unique constraint | Low |
| 2 | Deduplication | Solid at job level via SHA-256 + DB constraint | None |
| 3 | Same data on re-run | Updates `last_seen_at` only, no skipping | None (intentional) |
| 4 | Error handling | Good layering; missing retry logic and re-enrichment | Medium |
| 5 | Pagination | Hybrid cursor/offset; search has 3 separate count queries | Low |
| 6 | Startup checks | Safe; seed_cities has N+1 pattern | Low |
| 7 | 10+ ATS scaling | Sequential is fine now; needs semaphore at 500+ companies | Low-Medium |
| 8 | Ingestion vs Discovery vs Enrich | Clean separation; clearly defined roles | None |
| 9 | Logging | Well-calibrated; missing correlation IDs and timing | Low |
| 10 | Time intervals | Enrich scheduler becomes no-op; no re-enrichment | Medium |
| 11 | Idempotency & atomicity | Good; discovery has unguarded check-then-act race | Medium |
| 12 | Search & DB ops | FTS index correct; pool size tight; index coverage good | Low |
