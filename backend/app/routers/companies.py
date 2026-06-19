from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Query as OrmQuery
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.normalizer import canonicalize_city
from app.models import Company, Job
from app.routers._builders import build_company_response, build_job_response
from app.schemas import (
    CompanyBriefResponse,
    CompanyJobsResponse,
    CompanyResponse,
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
    for r in rows:
        result.setdefault(r.company_id, []).append(r.role_category)
    return result


def _company_query_with_counts(db: Session, city: str | None = None) -> OrmQuery:
    """Return a base query joining Company with active job counts via a subquery."""
    job_count_q = db.query(Job.company_id, func.count(Job.id).label("job_count")).filter(
        Job.is_active.is_(True)
    )
    if city:
        job_count_q = job_count_q.filter(Job.city == city)
    job_count_sq = job_count_q.group_by(Job.company_id).subquery()
    return db.query(
        Company, func.coalesce(job_count_sq.c.job_count, 0).label("job_count")
    ).outerjoin(job_count_sq, job_count_sq.c.company_id == Company.id)


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
    """Return a paginated list of active companies with optional filters."""
    canonical_city = canonicalize_city(city) if city else None
    effective_city = canonical_city or city if city else None

    base = _company_query_with_counts(db, city=effective_city).filter(Company.is_active.is_(True))

    if effective_city:
        city_company_ids = (
            db.query(Job.company_id)
            .filter(Job.city == effective_city, Job.is_active.is_(True))
            .distinct()
            .subquery()
        )
        base = base.filter(Company.id.in_(city_company_ids))
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


@router.get("/{slug}", response_model=CompanyResponse)
def get_company(slug: str, db: Session = Depends(get_db)):
    """Return detail for a single company by slug, including job count and open role categories."""
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    job_count = (
        db.query(func.count(Job.id))
        .filter(Job.company_id == company.id, Job.is_active.is_(True))
        .scalar()
        or 0
    )
    categories = _bulk_categories([company.id], db).get(company.id, [])

    data = CompanyResponse.model_validate(company)
    data.job_count = job_count
    data.open_role_categories = sorted(categories)
    return data


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
        has_more=(offset + len(jobs)) < total,
        limit=limit,
        offset=offset,
    )
