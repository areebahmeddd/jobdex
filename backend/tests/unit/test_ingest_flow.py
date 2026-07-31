"""Unit tests for BaseIngester.ingest() orchestration against a SQLite-backed session.

These cover the parts of the crawl that no single ingester owns: dedup, the hydrate
hook firing only for new postings, soft-deactivation, and blocked locations.
"""

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.ingestion.base import BaseIngester
from app.models import Company, Job


@compiles(JSONB, "sqlite")
def _render_jsonb_as_json(type_, compiler, **kw):
    """Let the JSONB columns build on SQLite so these tests need no live Postgres."""
    return "JSON"


@pytest.fixture
def db():
    """In-memory SQLite session holding the two tables the ingest path writes to.

    The tables are copied into a throwaway MetaData with their indexes dropped, because
    the GIN and partial indexes on Job are Postgres-only. Dedup is asserted through the
    ingester's own bookkeeping rather than the unique index, which is the behaviour worth
    pinning anyway.
    """
    meta = MetaData()
    for table in (Company.__table__, Job.__table__):
        table.to_metadata(meta).indexes.clear()

    engine = create_engine("sqlite://")
    meta.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


class FakeIngester(BaseIngester):
    """Ingester over a fixed payload that records how often hydrate() was asked for."""

    ats_type = "fake"

    def __init__(self, raw_jobs):
        self.raw_jobs = raw_jobs
        self.hydrate_calls: list[list[str]] = []

    async def fetch_raw(self, slug):
        return list(self.raw_jobs)

    def extract_job_id(self, raw):
        return str(raw["id"])

    async def hydrate(self, raw_jobs, slug):
        self.hydrate_calls.append([str(r["id"]) for r in raw_jobs])
        return [{**r, "detail": f"detail-{r['id']}"} for r in raw_jobs]

    def build_job(self, raw, company, slug):
        return Job(
            company_id=company.id,
            title=raw["title"],
            description=raw.get("detail", ""),
            city=raw.get("city"),
            country_code=raw.get("country_code"),
            source_url=f"https://example.test/{raw['id']}",
            ats_type=self.ats_type,
            ats_job_id=str(raw["id"]),
            is_active=True,
        )


def make_company(db):
    """Create the company with coordinates already set, which skips the Clearbit
    geo lookup ingest() would otherwise make on a company with no latitude."""
    company = Company(
        name="Acme",
        slug="acme",
        ats_type="fake",
        ats_slug="acme",
        city="Berlin",
        country_code="DE",
        latitude=52.52,
        longitude=13.405,
    )
    db.add(company)
    db.commit()
    return company


JOBS = [
    {"id": 1, "title": "Backend Engineer", "city": "Berlin", "country_code": "DE"},
    {"id": 2, "title": "Data Analyst", "city": "London", "country_code": "GB"},
]


@pytest.mark.anyio
async def test_first_run_inserts_and_hydrates_everything(db):
    make_company(db)
    ing = FakeIngester(JOBS)

    result = await ing.ingest("acme", db)

    assert result.new_jobs == 2
    assert result.updated_jobs == 0
    assert ing.hydrate_calls == [["1", "2"]]
    assert db.query(Job).count() == 2
    # hydrate output must reach build_job
    assert db.query(Job).filter(Job.ats_job_id == "1").one().description == "detail-1"


@pytest.mark.anyio
async def test_second_run_does_not_hydrate_known_jobs(db):
    make_company(db)
    ing = FakeIngester(JOBS)
    await ing.ingest("acme", db)
    ing.hydrate_calls.clear()

    result = await ing.ingest("acme", db)

    assert result.new_jobs == 0
    assert result.updated_jobs == 2
    assert ing.hydrate_calls == [], "known postings must not trigger a detail fetch"


@pytest.mark.anyio
async def test_only_the_new_posting_is_hydrated(db):
    make_company(db)
    ing = FakeIngester(JOBS)
    await ing.ingest("acme", db)
    ing.hydrate_calls.clear()

    ing.raw_jobs = JOBS + [
        {"id": 3, "title": "Product Manager", "city": "Paris", "country_code": "FR"}
    ]
    result = await ing.ingest("acme", db)

    assert result.new_jobs == 1
    assert result.updated_jobs == 2
    assert ing.hydrate_calls == [["3"]]


@pytest.mark.anyio
async def test_missing_posting_is_deactivated_not_deleted(db):
    make_company(db)
    ing = FakeIngester(JOBS)
    await ing.ingest("acme", db)

    ing.raw_jobs = JOBS[:1]
    result = await ing.ingest("acme", db)

    assert result.deactivated_jobs == 1
    assert db.query(Job).count() == 2
    assert db.query(Job).filter(Job.ats_job_id == "2").one().is_active is False


@pytest.mark.anyio
async def test_returning_posting_is_reactivated(db):
    make_company(db)
    ing = FakeIngester(JOBS)
    await ing.ingest("acme", db)
    ing.raw_jobs = JOBS[:1]
    await ing.ingest("acme", db)

    ing.raw_jobs = JOBS
    await ing.ingest("acme", db)

    assert db.query(Job).filter(Job.ats_job_id == "2").one().is_active is True


@pytest.mark.anyio
async def test_duplicate_ids_in_one_response_insert_once(db):
    make_company(db)
    ing = FakeIngester([JOBS[0], JOBS[0]])

    result = await ing.ingest("acme", db)

    assert result.new_jobs == 1
    assert db.query(Job).count() == 1


@pytest.mark.anyio
async def test_blocked_location_is_skipped_and_not_deactivated_later(db):
    make_company(db)
    ing = FakeIngester(
        JOBS + [{"id": 9, "title": "DevOps Engineer", "city": "Haifa", "country_code": "IL"}]
    )

    result = await ing.ingest("acme", db)

    assert result.new_jobs == 2
    assert db.query(Job).filter(Job.ats_job_id == "9").count() == 0
    # A blocked posting must not be counted as seen, or it would look like a closure.
    assert result.deactivated_jobs == 0


@pytest.mark.anyio
async def test_unextractable_job_is_reported_not_fatal(db):
    make_company(db)
    ing = FakeIngester([JOBS[0], {"title": "no id field"}])

    result = await ing.ingest("acme", db)

    assert result.new_jobs == 1
    assert len(result.errors) == 1
    assert ing.hydrate_calls == [["1"]]


@pytest.mark.anyio
async def test_hydrate_defaults_to_passthrough(db):
    """An ATS whose list endpoint is complete needs no hydrate override."""
    make_company(db)

    class NoHydrate(FakeIngester):
        pass

    NoHydrate.hydrate = BaseIngester.hydrate
    ing = NoHydrate(JOBS)

    result = await ing.ingest("acme", db)

    assert result.new_jobs == 2
    assert db.query(Job).filter(Job.ats_job_id == "1").one().description == ""


@pytest.mark.anyio
async def test_hydrate_length_mismatch_falls_back_to_raw(db):
    make_company(db)

    class BadHydrate(FakeIngester):
        async def hydrate(self, raw_jobs, slug):
            return raw_jobs[:1]

    ing = BadHydrate(JOBS)

    result = await ing.ingest("acme", db)

    assert result.new_jobs == 2, "a broken hydrate must not drop postings"
    assert db.query(Job).filter(Job.ats_job_id == "1").one().description == ""
