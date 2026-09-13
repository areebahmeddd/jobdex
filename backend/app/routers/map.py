from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import City, Company, Job
from app.routers._filters import JobFilters
from app.schemas import CompanyOfficesResponse, MapCitiesResponse, MapCompaniesResponse

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/companies", response_model=MapCompaniesResponse)
def map_companies(
    lat_min: float | None = Query(None, ge=-90, le=90, description="South bound of viewport"),
    lat_max: float | None = Query(None, ge=-90, le=90, description="North bound of viewport"),
    lng_min: float | None = Query(None, ge=-180, le=180, description="West bound of viewport"),
    lng_max: float | None = Query(None, ge=-180, le=180, description="East bound of viewport"),
    filters: JobFilters = Depends(),
    response: Response = None,
    db: Session = Depends(get_db),
):
    """Return one pin per company per city it is hiring in, with that city's job count."""
    query = filters.without("city").apply(
        db.query(
            Company.id,
            Company.name,
            Company.slug,
            Job.city,
            Job.country_code,
            Job.region,
            Job.latitude,
            Job.longitude,
            Company.industry,
            Company.logo_url,
            func.count(Job.id).label("job_count"),
        )
        .join(Company, Job.company_id == Company.id)
        .filter(Job.is_active.is_(True), Company.is_active.is_(True), Job.latitude.isnot(None))
    )

    if lat_min is not None:
        query = query.filter(Job.latitude >= lat_min)
    if lat_max is not None:
        query = query.filter(Job.latitude <= lat_max)
    if lng_min is not None:
        query = query.filter(Job.longitude >= lng_min)
    if lng_max is not None:
        query = query.filter(Job.longitude <= lng_max)

    pins = query.group_by(
        Company.id, Job.city, Job.country_code, Job.region, Job.latitude, Job.longitude
    ).subquery("pins")

    # Every company's largest location outranks its second, so world zoom shows
    # each company once instead of one employer's forty offices.
    rank = (
        func.row_number()
        .over(partition_by=pins.c.id, order_by=pins.c.job_count.desc())
        .label("rank")
    )
    rows = db.query(pins, rank).order_by(rank, pins.c.job_count.desc()).limit(500).all()

    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=30"

    return {
        "companies": [
            {
                "id": row.id,
                "name": row.name,
                "slug": row.slug,
                "city": row.city,
                "country_code": row.country_code,
                "region": row.region,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "industry": row.industry or [],
                "logo_url": row.logo_url,
                "job_count": row.job_count,
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.get("/cities", response_model=MapCitiesResponse)
def map_cities(
    lat_min: float | None = Query(None, ge=-90, le=90, description="South bound of viewport"),
    lat_max: float | None = Query(None, ge=-90, le=90, description="North bound of viewport"),
    lng_min: float | None = Query(None, ge=-180, le=180, description="West bound of viewport"),
    lng_max: float | None = Query(None, ge=-180, le=180, description="East bound of viewport"),
    filters: JobFilters = Depends(),
    response: Response = None,
    db: Session = Depends(get_db),
):
    """Return city cluster pins with aggregated job and company counts for the map UI."""
    # A city pin is what selecting that city would return, so its own filter is dropped.
    job_agg_query = filters.without("city", "country_code", "region").apply(
        db.query(
            City.id.label("city_id"),
            func.count(Job.id).label("job_count"),
            func.count(distinct(Job.company_id)).label("company_count"),
        )
        .join(Job, Job.city == City.name)
        .filter(Job.is_active.is_(True), City.latitude.isnot(None))
    )

    job_agg = job_agg_query.group_by(City.id).subquery("job_agg")

    city_query = (
        db.query(
            City,
            job_agg.c.job_count,
            job_agg.c.company_count,
        )
        .join(job_agg, job_agg.c.city_id == City.id)
        .filter(City.latitude.isnot(None), job_agg.c.job_count > 0)
    )

    if filters.region:
        city_query = city_query.filter(City.region == filters.region)
    if filters.country_code:
        city_query = city_query.filter(City.country_code == filters.country_code)

    if lat_min is not None:
        city_query = city_query.filter(City.latitude >= lat_min)
    if lat_max is not None:
        city_query = city_query.filter(City.latitude <= lat_max)
    if lng_min is not None:
        city_query = city_query.filter(City.longitude >= lng_min)
    if lng_max is not None:
        city_query = city_query.filter(City.longitude <= lng_max)

    rows = city_query.order_by(City.name).limit(500).all()

    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=30"

    return {
        "cities": [
            {
                "name": row.City.name,
                "slug": row.City.slug,
                "latitude": row.City.latitude,
                "longitude": row.City.longitude,
                "country_code": row.City.country_code,
                "region": row.City.region,
                "job_count": row.job_count,
                "company_count": row.company_count,
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.get("/companies/{slug}/offices", response_model=CompanyOfficesResponse)
def company_offices(slug: str, response: Response = None, db: Session = Depends(get_db)):
    """Return distinct office locations derived from active jobs for the given company slug."""
    company = db.query(Company).filter(Company.slug == slug, Company.is_active.is_(True)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    rows = (
        db.query(
            Job.city,
            Job.country_code,
            func.avg(Job.latitude).label("latitude"),
            func.avg(Job.longitude).label("longitude"),
            func.count(Job.id).label("job_count"),
        )
        .filter(
            Job.company_id == company.id,
            Job.is_active.is_(True),
            Job.city.isnot(None),
            Job.latitude.isnot(None),
        )
        .group_by(Job.city, Job.country_code)
        .order_by(func.count(Job.id).desc())
        .all()
    )

    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=30"

    return {
        "offices": [
            {
                "city": row.city,
                "country_code": row.country_code,
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
                "job_count": row.job_count,
            }
            for row in rows
        ]
    }
