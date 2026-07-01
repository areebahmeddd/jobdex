from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.normalizer import canonicalize_city
from app.models import Company, Job
from app.routers._builders import build_company_response, build_job_response
from app.schemas import SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    city: str | None = Query(
        None, description="City name (supports aliases: 'Bengaluru', 'NCR', 'NYC'...)"
    ),
    role: str | None = Query(
        None,
        description="Role category: engineering, design, product, data, marketing, sales, finance, operations, healthcare, hospitality...",
    ),
    industry: str | None = Query(
        None, description="Industry tag partial match: fintech, saas, ai..."
    ),
    country_code: str | None = Query(None, description="ISO-2 country code: IN, AE, GB, US..."),
    region: str | None = Query(
        None, description="Region: south_asia, middle_east, europe, north_america..."
    ),
    is_remote: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Search jobs and companies across all combinable filters and return a unified response."""
    query = (
        db.query(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .filter(Job.is_active.is_(True), Company.is_active.is_(True))
    )

    if city:
        canonical = canonicalize_city(city) or city
        query = query.filter(Job.city == canonical)

    if role:
        query = query.filter(Job.role_category == role.lower())

    if country_code:
        query = query.filter(Job.country_code == country_code.upper())

    if region:
        query = query.filter(Job.region == region.lower())

    if is_remote is not None:
        query = query.filter(Job.is_remote.is_(is_remote))

    if industry:
        query = query.filter(Company.industry.cast(JSONB).contains([industry.lower()]))

    total_jobs = query.count()
    total_companies_count = (
        query.with_entities(func.count(func.distinct(Job.company_id))).scalar() or 0
    )

    paged_rows = query.order_by(Job.posted_at.desc()).offset(offset).limit(limit).all()

    page_company_jobs: dict[str, tuple[Company, list[Job]]] = {}
    for job, co in paged_rows:
        if co.id not in page_company_jobs:
            page_company_jobs[co.id] = (co, [])
        page_company_jobs[co.id][1].append(job)

    companies_out = [
        build_company_response(co, len(jobs), [j.role_category for j in jobs if j.role_category])
        for co, jobs in page_company_jobs.values()
    ]
    jobs_out = [build_job_response(job, co) for job, co in paged_rows]

    return SearchResponse(
        companies=companies_out,
        jobs=jobs_out,
        total_companies=total_companies_count,
        total_jobs=total_jobs,
        offset=offset,
        limit=limit,
    )
