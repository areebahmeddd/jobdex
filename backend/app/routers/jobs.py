"""Job listing and detail endpoints.

GET /jobs       paginated job listing with filters
GET /jobs/{id}  full job detail
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.normalizer import canonicalize_city
from app.models import Company, Job
from app.schemas import JobDetailResponse, JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _enrich(job: Job, company: Company) -> JobResponse:
    data = JobResponse.model_validate(job)
    data.company_name = company.name
    data.company_slug = company.slug
    data.company_logo_url = company.logo_url
    return data


def _enrich_detail(job: Job, company: Company) -> JobDetailResponse:
    data = JobDetailResponse.model_validate(job)
    data.company_name = company.name
    data.company_slug = company.slug
    data.company_logo_url = company.logo_url
    return data


@router.get("", response_model=dict)
def list_jobs(
    city: str | None = Query(None),
    country_code: str | None = Query(None),
    region: str | None = Query(None, description="e.g. south_asia, middle_east, europe"),
    role_category: str | None = Query(None),
    role_subcategory: str | None = Query(None),
    seniority: str | None = Query(None),
    is_remote: bool | None = Query(None),
    q: str | None = Query(None, description="Free-text search on title"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .filter(Job.is_active.is_(True))
    )

    if city:
        canonical = canonicalize_city(city) or city
        query = query.filter(Job.city == canonical)
    if country_code:
        query = query.filter(Job.country_code == country_code.upper())
    if region:
        query = query.filter(Job.region == region.lower())
    if role_category:
        query = query.filter(Job.role_category == role_category.lower())
    if role_subcategory:
        query = query.filter(Job.role_subcategory == role_subcategory.lower())
    if seniority:
        query = query.filter(Job.seniority == seniority.lower())
    if is_remote is not None:
        query = query.filter(Job.is_remote.is_(is_remote))
    if q:
        query = query.filter(Job.title.ilike(f"%{q}%"))

    total = query.count()
    rows = query.order_by(Job.posted_at.desc()).offset(offset).limit(limit).all()

    return {
        "jobs": [_enrich(j, c).model_dump() for j, c in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    row = (
        db.query(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .filter(Job.id == job_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return _enrich_detail(row[0], row[1])
