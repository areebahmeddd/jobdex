"""City listing and detail endpoints.

GET /cities        all known cities with live job/company counts
GET /cities/{slug} single city detail
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import City, Company, Job
from app.schemas import CityResponse

router = APIRouter(prefix="/cities", tags=["cities"])


def _enrich(city: City, db: Session) -> CityResponse:
    job_count = (
        db.query(func.count(Job.id)).filter(Job.is_active.is_(True), Job.city == city.name).scalar()
    ) or 0

    company_count = (
        db.query(func.count(Company.id))
        .filter(Company.is_active.is_(True), Company.city == city.name)
        .scalar()
    ) or 0

    return CityResponse(
        id=city.id,
        name=city.name,
        slug=city.slug,
        country=city.country,
        country_code=city.country_code,
        region=city.region,
        latitude=city.latitude,
        longitude=city.longitude,
        description=city.description,
        is_featured=city.is_featured,
        job_count=job_count,
        company_count=company_count,
    )


@router.get("", response_model=list[CityResponse])
def list_cities(
    region: str | None = Query(None, description="Filter by region slug"),
    country_code: str | None = Query(None),
    featured_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = db.query(City)
    if featured_only:
        q = q.filter(City.is_featured.is_(True))
    if region:
        q = q.filter(City.region == region.lower())
    if country_code:
        q = q.filter(City.country_code == country_code.upper())
    cities = q.order_by(City.name).all()
    return [_enrich(c, db) for c in cities]


@router.get("/{slug}", response_model=CityResponse)
def get_city(slug: str, db: Session = Depends(get_db)):
    city = db.query(City).filter(City.slug == slug).first()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    return _enrich(city, db)
