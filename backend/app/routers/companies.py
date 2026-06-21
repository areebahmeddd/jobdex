from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Query as OrmQuery
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.normalizer import canonicalize_city
from app.models import Company, Job
from app.routers._builders import (
    build_company_detail_response,
    build_company_response,
    build_job_response,
)
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


def _company_query_with_counts(db: Session, city: str | None = None) -> OrmQuery:
    """Return a base query joining Company with active job counts via a subquery."""
    job_count_q = db.query(Job.company_id, func.count(Job.id).label("job_count")).filter(
        Job.is_active.is_(True)
    )
    if city:
        job_count_q = job_count_q.filter(Job.city == city)
    job_count_sq = job_count_q.group_by(Job.company_id).subquery()
    query = db.query(Company, func.coalesce(job_count_sq.c.job_count, 0).label("job_count"))
    if city:
        return query.join(job_count_sq, job_count_sq.c.company_id == Company.id)
    return query.outerjoin(job_count_sq, job_count_sq.c.company_id == Company.id)


@router.get("", response_model=PaginatedCompaniesResponse)
def list_companies(
    city: str | None = Query(None),
    country_code: str | None = Query(None),
    region: str | None = Query(None),
    industry: str | None = Query(None),
    stage: str | None = Query(None),
    ats_type: str | None = Query(None),
    q: str | None = Query(None, description="Search company name / description"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    canonical_city = canonicalize_city(city) if city else None
    effective_city = canonical_city or city if city else None

    base = _company_query_with_counts(db, city=effective_city).filter(Company.is_active.is_(True))

    if country_code:
        base = base.filter(Company.country_code == country_code.upper())
    if region:
        base = base.filter(Company.region == region.lower())
    if stage:
        base = base.filter(Company.stage == stage.lower())
    if ats_type:
        base = base.filter(Company.ats_type == ats_type.lower())
    if q:
        base = base.filter(Company.name.ilike(f"%{q}%") | Company.description.ilike(f"%{q}%"))
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

    dept_rows = (
        db.query(Job.department)
        .filter(
            Job.company_id == company.id,
            Job.is_active.is_(True),
            Job.department.isnot(None),
        )
        .distinct()
        .all()
    )
    departments = [r.department for r in dept_rows]

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
    city: str | None = Query(None),
    country_code: str | None = Query(None),
    role_category: str | None = Query(None),
    seniority: str | None = Query(None),
    is_remote: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return paginated active jobs for a company, with optional city, role, and seniority filters."""
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    query = db.query(Job).filter(Job.company_id == company.id, Job.is_active.is_(True))

    if city:
        canonical = canonicalize_city(city) or city
        query = query.filter(Job.city == canonical)
    if country_code:
        query = query.filter(Job.country_code == country_code.upper())
    if role_category:
        query = query.filter(Job.role_category == role_category.lower())
    if seniority:
        query = query.filter(Job.seniority == seniority.lower())
    if is_remote is not None:
        query = query.filter(Job.is_remote.is_(is_remote))

    total = query.count()
    jobs = query.order_by(Job.posted_at.desc()).offset(offset).limit(limit).all()

    return CompanyJobsResponse(
        company=CompanyBriefResponse.model_validate(company),
        jobs=[build_job_response(j, company) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )
