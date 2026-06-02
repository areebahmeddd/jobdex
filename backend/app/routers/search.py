"""Primary map-first discovery endpoint.

GET /search  all filters optional and combinable:
  city, role, industry, country_code, region, is_remote
"""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.normalizer import canonicalize_city
from app.models import Company, Job
from app.schemas import CompanyResponse, JobResponse, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


def _build_company(company: Company, jobs: list[Job]) -> CompanyResponse:
    data = CompanyResponse.model_validate(company)
    data.job_count = len(jobs)
    data.open_role_categories = sorted({j.role_category for j in jobs if j.role_category})
    return data


def _build_job(job: Job, company: Company) -> JobResponse:
    data = JobResponse.model_validate(job)
    data.company_name = company.name
    data.company_slug = company.slug
    data.company_logo_url = company.logo_url
    return data


@router.get("", response_model=SearchResponse)
def search(
    city: str | None = Query(
        None, description="City name (supports aliases: 'Bengaluru', 'NCR', 'NYC'…)"
    ),
    role: str | None = Query(
        None, description="Role category: engineering, design, product, sales…"
    ),
    industry: str | None = Query(
        None, description="Industry tag partial match: fintech, saas, ai…"
    ),
    country_code: str | None = Query(None, description="ISO-2 country code: IN, AE, GB, US…"),
    region: str | None = Query(
        None, description="Region: south_asia, middle_east, europe, north_america…"
    ),
    is_remote: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit

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

    all_rows: Sequence[tuple[Job, Company]] = q.order_by(Job.posted_at.desc()).all()

    # Industry filter runs in Python; SQLite has no JSON column index.
    if industry:
        low = industry.lower()
        all_rows = [
            (job, co)
            for job, co in all_rows
            if any(low in tag.lower() for tag in (co.industry or []))
        ]

    total_jobs = len(all_rows)

    # Group companies from the matching job set.
    company_jobs: dict[str, tuple[Company, list[Job]]] = {}
    for job, co in all_rows:
        if co.id not in company_jobs:
            company_jobs[co.id] = (co, [])
        company_jobs[co.id][1].append(job)

    total_companies = len(company_jobs)

    # Paginate.
    paged = all_rows[offset : offset + limit]
    paged_company_ids = {co.id for _, co in paged}

    companies_out = [
        _build_company(co, jobs)
        for co_id, (co, jobs) in company_jobs.items()
        if co_id in paged_company_ids
    ]
    jobs_out = [_build_job(job, co) for job, co in paged]

    return SearchResponse(
        companies=companies_out,
        jobs=jobs_out,
        total_companies=total_companies,
        total_jobs=total_jobs,
        page=page,
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
