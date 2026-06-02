"""Company listing and detail endpoints.

GET /companies              paginated listing with filters
GET /companies/{slug}       company detail with active jobs
GET /companies/{slug}/jobs  jobs for a single company
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.normalizer import canonicalize_city
from app.models import Company, Job
from app.schemas import CompanyDetailResponse, CompanyResponse, JobResponse

router = APIRouter(prefix="/companies", tags=["companies"])


def _job_response(job: Job, company: Company) -> JobResponse:
    data = JobResponse.model_validate(job)
    data.company_name = company.name
    data.company_slug = company.slug
    data.company_logo_url = company.logo_url
    return data


def _company_response(company: Company, db: Session) -> CompanyResponse:
    job_count = (
        db.query(func.count(Job.id))
        .filter(Job.company_id == company.id, Job.is_active.is_(True))
        .scalar()
    ) or 0

    categories = [
        row[0]
        for row in db.query(Job.role_category)
        .filter(
            Job.company_id == company.id,
            Job.is_active.is_(True),
            Job.role_category.isnot(None),
        )
        .distinct()
        .all()
        if row[0]
    ]

    data = CompanyResponse.model_validate(company)
    data.job_count = job_count
    data.open_role_categories = categories
    return data


@router.get("", response_model=dict)
def list_companies(
    city: str | None = Query(None),
    country_code: str | None = Query(None),
    region: str | None = Query(None, description="e.g. south_asia, middle_east"),
    industry: str | None = Query(None, description="Partial match on industry tags"),
    stage: str | None = Query(None),
    ats_type: str | None = Query(None),
    q: str | None = Query(None, description="Search company name / description"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Company).filter(Company.is_active.is_(True))

    if city:
        canonical = canonicalize_city(city) or city
        query = query.filter(Company.city == canonical)
    if country_code:
        query = query.filter(Company.country_code == country_code.upper())
    if region:
        query = query.filter(Company.region == region.lower())
    if stage:
        query = query.filter(Company.stage == stage.lower())
    if ats_type:
        query = query.filter(Company.ats_type == ats_type.lower())
    if q:
        query = query.filter(Company.name.ilike(f"%{q}%") | Company.description.ilike(f"%{q}%"))

    all_companies = query.order_by(Company.name).all()

    # Industry filter runs in Python because SQLite has no JSON index.
    if industry:
        low = industry.lower()
        all_companies = [
            c for c in all_companies if any(low in tag.lower() for tag in (c.industry or []))
        ]

    total = len(all_companies)
    paged = all_companies[offset : offset + limit]
    results = [_company_response(c, db) for c in paged]

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

    active_jobs = (
        db.query(Job)
        .filter(Job.company_id == company.id, Job.is_active.is_(True))
        .order_by(Job.posted_at.desc())
        .all()
    )

    data = CompanyDetailResponse.model_validate(company)
    data.jobs = [_job_response(j, company) for j in active_jobs]
    data.job_count = len(data.jobs)
    data.open_role_categories = list({j.role_category for j in active_jobs if j.role_category})
    return data


@router.get("/{slug}/jobs", response_model=dict)
def company_jobs(
    slug: str,
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
            "name": company.name,
            "slug": company.slug,
            "city": company.city,
            "latitude": company.latitude,
            "longitude": company.longitude,
        },
        "jobs": [_job_response(j, company).model_dump() for j in jobs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
