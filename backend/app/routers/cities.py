"""City listing and detail endpoints.

GET /cities        paginated city list with live job/company counts
GET /cities/{slug} single city detail
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import City, Job
from app.schemas import CityResponse

router = APIRouter(prefix="/cities", tags=["cities"])


def _counts_by_city(db: Session, city_names: list[str]) -> dict[str, tuple[int, int]]:
    """Return {city_name: (job_count, company_count)} for the given city names."""
    if not city_names:
        return {}
    rows = (
        db.query(
            Job.city,
            func.count(Job.id).label("job_count"),
            func.count(func.distinct(Job.company_id)).label("company_count"),
        )
        .filter(Job.is_active.is_(True), Job.city.in_(city_names))
        .group_by(Job.city)
        .all()
    )
    return {r.city: (r.job_count, r.company_count) for r in rows}


def _build_city_response(city: City, job_count: int, company_count: int) -> CityResponse:
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


@router.get("", response_model=dict)
def list_cities(
    region: str | None = Query(None),
    country_code: str | None = Query(None),
    featured_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(City)
    if featured_only:
        q = q.filter(City.is_featured.is_(True))
    if region:
        q = q.filter(City.region == region.lower())
    if country_code:
        q = q.filter(City.country_code == country_code.upper())

    total = q.count()
    cities = q.order_by(City.name).offset(offset).limit(limit).all()

    names = [c.name for c in cities]
    counts = _counts_by_city(db, names)

    return {
        "cities": [
            _build_city_response(c, *counts.get(c.name, (0, 0))).model_dump() for c in cities
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{slug}", response_model=CityResponse)
def get_city(slug: str, db: Session = Depends(get_db)):
    city = db.query(City).filter(City.slug == slug).first()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    counts = _counts_by_city(db, [city.name])
    job_count, company_count = counts.get(city.name, (0, 0))
    return _build_city_response(city, job_count, company_count)
