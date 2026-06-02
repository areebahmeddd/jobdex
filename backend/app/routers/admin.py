"""Admin and ingestion endpoints.

POST /ingest/greenhouse/{slug}  ingest a Greenhouse board
POST /ingest/lever/{slug}       ingest a Lever board
POST /ingest/ashby/{slug}       ingest an Ashby board
POST /ingest/discover/{slug}    probe all three ATS types, ingest the first match
GET  /stats                     aggregate stats
POST /admin/reset               delete all jobs (dev)
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.ingestion import INGESTERS, ashby, greenhouse, lever
from app.models import City, Company, Job
from app.schemas import DiscoverResult, IngestResult, StatsResponse

router = APIRouter(tags=["admin"])

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _check_admin(api_key: str | None = Security(_api_key_header)):
    if settings.ADMIN_API_KEY and api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing X-API-Key header")


# Per-ATS ingestion


@router.post("/ingest/greenhouse/{slug}", response_model=IngestResult)
async def ingest_greenhouse(
    slug: str,
    db: Session = Depends(get_db),
    _: None = Depends(_check_admin),
):
    return await greenhouse.ingest(slug.lower(), db)


@router.post("/ingest/lever/{slug}", response_model=IngestResult)
async def ingest_lever(
    slug: str,
    db: Session = Depends(get_db),
    _: None = Depends(_check_admin),
):
    return await lever.ingest(slug.lower(), db)


@router.post("/ingest/ashby/{slug}", response_model=IngestResult)
async def ingest_ashby(
    slug: str,
    db: Session = Depends(get_db),
    _: None = Depends(_check_admin),
):
    return await ashby.ingest(slug.lower(), db)


# Auto-discover


@router.post("/ingest/discover/{slug}", response_model=DiscoverResult)
async def discover_and_ingest(
    slug: str,
    db: Session = Depends(get_db),
    _: None = Depends(_check_admin),
):
    """Probe Greenhouse, Lever, then Ashby in order. Ingest from the first match."""
    slug = slug.lower()
    discovery_order = ["greenhouse", "lever", "ashby"]

    for ats_name in discovery_order:
        ingester = INGESTERS[ats_name]
        try:
            found = await ingester.probe(slug)
        except Exception:
            found = False

        if found:
            result = await ingester.ingest(slug, db)
            return DiscoverResult(
                company_slug=slug,
                ats_type=ats_name,
                discovered=True,
                message=f"Found on {ats_name} - {result.new_jobs} new jobs ingested",
                ingest_result=result,
            )
        await asyncio.sleep(0.3)

    return DiscoverResult(
        company_slug=slug,
        discovered=False,
        message="Not found on Greenhouse, Lever, or Ashby. Check the slug or try a different ATS.",
    )


# Stats


@router.get("/stats", response_model=StatsResponse)
def stats(db: Session = Depends(get_db)):
    total_companies = db.query(func.count(Company.id)).scalar() or 0
    total_jobs = db.query(func.count(Job.id)).scalar() or 0
    active_jobs = db.query(func.count(Job.id)).filter(Job.is_active.is_(True)).scalar() or 0
    total_cities = db.query(func.count(City.id)).scalar() or 0

    cities_with_jobs = (
        db.query(func.count(func.distinct(Job.city)))
        .filter(Job.is_active.is_(True), Job.city.isnot(None))
        .scalar()
    ) or 0

    role_rows = (
        db.query(Job.role_category, func.count(Job.id))
        .filter(Job.is_active.is_(True), Job.role_category.isnot(None))
        .group_by(Job.role_category)
        .order_by(func.count(Job.id).desc())
        .all()
    )
    role_categories = {r[0]: r[1] for r in role_rows}

    city_rows = (
        db.query(Job.city, func.count(Job.id))
        .filter(Job.is_active.is_(True), Job.city.isnot(None))
        .group_by(Job.city)
        .order_by(func.count(Job.id).desc())
        .limit(10)
        .all()
    )
    top_cities = [{"city": r[0], "job_count": r[1]} for r in city_rows]

    region_rows = (
        db.query(Job.region, func.count(Job.id))
        .filter(Job.is_active.is_(True), Job.region.isnot(None))
        .group_by(Job.region)
        .order_by(func.count(Job.id).desc())
        .all()
    )
    top_regions = [{"region": r[0], "job_count": r[1]} for r in region_rows]

    ats_rows = (
        db.query(Company.ats_type, func.count(Company.id))
        .filter(Company.ats_type.isnot(None))
        .group_by(Company.ats_type)
        .all()
    )
    ats_breakdown = {r[0]: r[1] for r in ats_rows}

    return StatsResponse(
        total_companies=total_companies,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_cities=total_cities,
        cities_with_jobs=cities_with_jobs,
        role_categories=role_categories,
        top_cities=top_cities,
        top_regions=top_regions,
        ats_breakdown=ats_breakdown,
    )


# Reset


@router.post("/admin/reset", response_model=dict)
def reset_database(
    db: Session = Depends(get_db),
    _: None = Depends(_check_admin),
):
    """Delete all jobs and reset company crawl state. Keeps companies and cities."""
    deleted = db.query(Job).delete()
    db.query(Company).update({"last_crawled_at": None, "crawl_error": None})
    db.commit()
    return {
        "deleted_jobs": deleted,
        "message": "Jobs cleared. Companies and cities retained.",
    }
