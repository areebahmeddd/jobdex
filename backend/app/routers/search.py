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
        None, description="Role category: engineering, design, product, sales..."
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
    q = (
        db.query(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .filter(Job.is_active.is_(True), Company.is_active.is_(True))
    )

    if city:
        canonical = canonicalize_city(city) or city
        q = q.filter(Job.city == canonical)

    if role:
        q = q.filter(Job.role_category == role.lower())

    if country_code:
        q = q.filter(Job.country_code == country_code.upper())

    if region:
        q = q.filter(Job.region == region.lower())

    if is_remote is not None:
        q = q.filter(Job.is_remote.is_(is_remote))

    if industry:
        q = q.filter(Company.industry.cast(JSONB).contains([industry.lower()]))

    total_jobs = q.count()
    total_companies = (
        db.query(func.count(func.distinct(Job.company_id)))
        .join(Company, Job.company_id == Company.id)
        .filter(Job.is_active.is_(True), Company.is_active.is_(True))
    )

    # Mirror filters for distinct company count.
    if city:
        canonical = canonicalize_city(city) or city
        total_companies = total_companies.filter(Job.city == canonical)
    if role:
        total_companies = total_companies.filter(Job.role_category == role.lower())
    if country_code:
        total_companies = total_companies.filter(Job.country_code == country_code.upper())
    if region:
        total_companies = total_companies.filter(Job.region == region.lower())
    if is_remote is not None:
        total_companies = total_companies.filter(Job.is_remote.is_(is_remote))
    if industry:
        total_companies = total_companies.filter(
            Company.industry.cast(JSONB).contains([industry.lower()])
        )

    total_companies_count = total_companies.scalar() or 0

    paged_rows = q.order_by(Job.posted_at.desc()).offset(offset).limit(limit).all()

    # Per-company aggregation for this page.
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
        filters={
            "city": city,
            "role": role,
            "industry": industry,
            "country_code": country_code,
            "region": region,
            "is_remote": is_remote,
        },
    )
