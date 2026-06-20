from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import City, Job
from app.routers._builders import build_city_response
from app.schemas import CityResponse, PaginatedCitiesResponse

router = APIRouter(prefix="/cities", tags=["cities"])


def _counts_by_city(db: Session, city_names: list[str]) -> dict[str, tuple[int, int]]:
    """Return job and company counts keyed by city name for the given list of cities."""
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


@router.get("", response_model=PaginatedCitiesResponse)
def list_cities(
    region: str | None = Query(None),
    country_code: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    response: Response = None,
    db: Session = Depends(get_db),
):
    """Return a paginated list of cities with live job and company counts."""
    q = db.query(City)
    if region:
        q = q.filter(City.region == region.lower())
    if country_code:
        q = q.filter(City.country_code == country_code.upper())

    total = q.count()
    cities = q.order_by(City.name).offset(offset).limit(limit).all()

    names = [c.name for c in cities]
    counts = _counts_by_city(db, names)

    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"

    return PaginatedCitiesResponse(
        cities=[build_city_response(c, *counts.get(c.name, (0, 0))) for c in cities],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{slug}", response_model=CityResponse)
def get_city(slug: str, response: Response = None, db: Session = Depends(get_db)):
    """Return detail for a single city by slug, including live job and company counts."""
    city = db.query(City).filter(City.slug == slug).first()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    counts = _counts_by_city(db, [city.name])
    job_count, company_count = counts.get(city.name, (0, 0))
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    return build_city_response(city, job_count, company_count)
