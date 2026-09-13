from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Query as OrmQuery
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, Job
from app.routers._builders import (
    build_company_detail_response,
    build_company_response,
    build_job_response,
)
from app.routers._filters import JobFilters
from app.schemas import (
    CompanyBriefResponse,
    CompanyDetailResponse,
    CompanyJobsResponse,
    PaginatedCompaniesResponse,
)

router = APIRouter(prefix="/companies", tags=["companies"])


def _bulk_categories(company_ids: list[str], db: Session) -> dict[str, list[str]]:
    """Return open role categories grouped by company ID for a batch of companies."""
    rows = (
        db.query(Job.company_id, Job.role_category)
        .filter(
            Job.company_id.in_(company_ids),
            Job.is_active.is_(True),
            Job.role_category.isnot(None),
        )
        .distinct()
        .all()
    )
    result: dict[str, list[str]] = {}
    for row in rows:
        result.setdefault(row.company_id, []).append(row.role_category)
    return result


def _company_query_with_counts(
    db: Session, filters: JobFilters | None = None, *, narrowed: bool = False
) -> OrmQuery:
    """Return a base query joining Company with active job counts via a subquery.

    A narrowed query joins inner, so companies with no matching job drop out.
    """
    job_count_q = db.query(Job.company_id, func.count(Job.id).label("job_count")).filter(
        Job.is_active.is_(True)
    )
    if filters is not None:
        job_count_q = filters.apply(job_count_q)
    job_count_sq = job_count_q.group_by(Job.company_id).subquery()
    query = db.query(Company, func.coalesce(job_count_sq.c.job_count, 0).label("job_count"))
    if narrowed:
        return query.join(job_count_sq, job_count_sq.c.company_id == Company.id)
    return query.outerjoin(job_count_sq, job_count_sq.c.company_id == Company.id)


@router.get("", response_model=PaginatedCompaniesResponse)
def list_companies(
    city: str | None = Query(None, description="Only companies hiring in this city"),
    role_category: list[str] | None = Query(
        None, description="Repeatable; only companies with an open role in these categories"
    ),
    seniority: list[str] | None = Query(None, description="Repeatable open-role seniority"),
    job_type: list[str] | None = Query(None, description="Repeatable open-role employment type"),
    work_mode: list[str] | None = Query(None, description="Repeatable: remote, hybrid, onsite"),
    is_remote: bool | None = Query(None, description="Legacy remote filter; prefer work_mode"),
    posted_within: int | None = Query(None, ge=1, le=365, description="Open-role recency in days"),
    country_code: str | None = Query(None, description="Only companies hiring in this country"),
    region: str | None = Query(None, description="Only companies hiring in this region"),
    industry: str | None = Query(None),
    stage: str | None = Query(None),
    ats_type: list[str] | None = Query(None, description="Repeatable ATS source"),
    has_errors: bool | None = Query(
        None, description="true = only companies with a crawl error; false = only error-free"
    ),
    q: str | None = Query(None, description="Search open roles and company names"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return a paginated company list, optionally narrowed to companies with matching open roles."""
    # Job-level params describe a company's open roles, so they filter the count
    # subquery, not the company row.
    job_filters = JobFilters(
        city=city,
        country_code=country_code,
        region=region,
        role_category=role_category,
        seniority=seniority,
        job_type=job_type,
        work_mode=work_mode,
        is_remote=is_remote,
        posted_within=posted_within,
        q=q,
    )
    base = _company_query_with_counts(db, job_filters, narrowed=job_filters.has_job_scope).filter(
        Company.is_active.is_(True)
    )

    if stage:
        base = base.filter(Company.stage == stage.lower())
    if ats_type:
        base = base.filter(Company.ats_type.in_([t.lower() for t in ats_type]))
    if has_errors is True:
        base = base.filter(Company.crawl_error.isnot(None))
    elif has_errors is False:
        base = base.filter(Company.crawl_error.is_(None))
    if industry:
        base = base.filter(Company.industry.cast(JSONB).contains([industry.lower()]))

    total = base.count()
    rows = base.order_by(Company.name).offset(offset).limit(limit).all()

    company_ids = [company.id for company, _ in rows]
    categories_map = _bulk_categories(company_ids, db)
    results = [
        build_company_response(company, job_count, categories_map.get(company.id, []))
        for company, job_count in rows
    ]

    return PaginatedCompaniesResponse(
        companies=results,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{slug}", response_model=CompanyDetailResponse)
def get_company(slug: str, db: Session = Depends(get_db)):
    """Return the full company profile by slug, including enriched and derived fields."""
    company = db.query(Company).filter(Company.slug == slug, Company.is_active.is_(True)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    job_count = (
        db.query(func.count(Job.id))
        .filter(Job.company_id == company.id, Job.is_active.is_(True))
        .scalar()
        or 0
    )
    categories = _bulk_categories([company.id], db).get(company.id, [])

    department_rows = (
        db.query(Job.department)
        .filter(
            Job.company_id == company.id,
            Job.is_active.is_(True),
            Job.department.isnot(None),
        )
        .distinct()
        .all()
    )
    departments = [row.department for row in department_rows]

    remote_rows = (
        db.query(Job.is_remote, Job.remote_type)
        .filter(Job.company_id == company.id, Job.is_active.is_(True))
        .distinct()
        .all()
    )
    work_modes: list[str] = []
    for is_remote, remote_type in remote_rows:
        if is_remote and remote_type == "hybrid" and "Hybrid" not in work_modes:
            work_modes.append("Hybrid")
        elif is_remote and "Remote" not in work_modes:
            work_modes.append("Remote")
        elif not is_remote and "On-site" not in work_modes:
            work_modes.append("On-site")

    return build_company_detail_response(company, job_count, categories, work_modes, departments)


@router.get("/{slug}/jobs", response_model=CompanyJobsResponse)
def list_company_jobs(
    slug: str,
    filters: JobFilters = Depends(),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return paginated active jobs for a company under the shared job filter set."""
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    query = filters.apply(
        db.query(Job).filter(Job.company_id == company.id, Job.is_active.is_(True))
    )

    total = query.count()
    jobs = (
        query.order_by(Job.posted_at.desc().nullslast(), Job.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return CompanyJobsResponse(
        company=CompanyBriefResponse.model_validate(company),
        jobs=[build_job_response(j, company) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )
