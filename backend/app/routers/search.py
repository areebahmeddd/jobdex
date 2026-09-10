from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, Job
from app.routers._builders import build_company_response, build_job_response
from app.routers._filters import JobFilters
from app.schemas import SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    filters: JobFilters = Depends(),
    industry: str | None = Query(
        None, description="Industry tag partial match: fintech, saas, ai..."
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Search jobs and companies across all combinable filters and return a unified response."""
    query = filters.apply(
        db.query(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .filter(Job.is_active.is_(True), Company.is_active.is_(True))
    )

    # Industry is a company attribute, so it is the one filter not in the shared set.
    if industry:
        query = query.filter(Company.industry.cast(JSONB).contains([industry.lower()]))

    total_jobs = query.count()
    total_companies_count = (
        query.with_entities(func.count(func.distinct(Job.company_id))).scalar() or 0
    )

    paged_rows = (
        query.order_by(Job.posted_at.desc().nullslast(), Job.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

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
