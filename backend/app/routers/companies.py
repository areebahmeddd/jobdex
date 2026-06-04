"""Company listing and detail endpoints.

GET /companies              paginated listing with filters
GET /companies/{slug}       company detail (no embedded jobs)
GET /companies/{slug}/jobs  paginated jobs for a single company
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.normalizer import canonicalize_city
from app.models import Company, Job
from app.schemas import CompanyDetailResponse, CompanyResponse, JobResponse

router = APIRouter(prefix="/companies", tags=["companies"])


def _build_job_response(job: Job, company: Company) -> JobResponse:
    data = JobResponse.model_validate(job)
    data.company_name = company.name
    data.company_slug = company.slug
    data.company_logo_url = company.logo_url
    return data


def _bulk_categories(company_ids: list[str], db: Session) -> dict[str, list[str]]:
    """Return {company_id: [role_category, ...]} for all given company IDs in one query."""
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


def _enriched_company_query(db: Session):
    """Return a base query with active job_count joined via subquery."""
    job_count_sq = (
        db.query(Job.company_id, func.count(Job.id).label("job_count"))
        .filter(Job.is_active.is_(True))
        .group_by(Job.company_id)
        .subquery()
    )
    return db.query(
        Company, func.coalesce(job_count_sq.c.job_count, 0).label("job_count")
    ).outerjoin(job_count_sq, job_count_sq.c.company_id == Company.id)


def _build_company_response(
    company: Company, job_count: int, categories: list[str]
) -> CompanyResponse:
    data = CompanyResponse.model_validate(company)
    data.job_count = job_count
    data.open_role_categories = sorted(categories)
    return data


@router.get("", response_model=dict)
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
    base = _enriched_company_query(db).filter(Company.is_active.is_(True))

    if city:
        canonical = canonicalize_city(city) or city
        base = base.filter(Company.city == canonical)
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
        _build_company_response(company, job_count, categories_map.get(company.id, []))
        for company, job_count in rows
    ]

    return {
        "companies": [r.model_dump() for r in results],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{slug}", response_model=CompanyDetailResponse)
def get_company(slug: str, db: Session = Depends(get_db)):
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

    data = CompanyDetailResponse.model_validate(company)
    data.job_count = job_count
    data.open_role_categories = sorted(categories)
    return data


@router.get("/{slug}/jobs", response_model=dict)
def company_jobs(
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

    return {
        "company": {
            "id": company.id,
            "name": company.name,
            "slug": company.slug,
            "city": company.city,
            "country_code": company.country_code,
            "latitude": company.latitude,
            "longitude": company.longitude,
            "logo_url": company.logo_url,
        },
        "jobs": [_build_job_response(j, company).model_dump() for j in jobs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
