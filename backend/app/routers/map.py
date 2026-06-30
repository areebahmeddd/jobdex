from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import City, Company, Job
from app.schemas import CompanyOfficesResponse, MapCitiesResponse, MapCompaniesResponse

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/companies", response_model=MapCompaniesResponse)
def map_companies(
    lat_min: float | None = Query(None, ge=-90, le=90, description="South bound of viewport"),
    lat_max: float | None = Query(None, ge=-90, le=90, description="North bound of viewport"),
    lng_min: float | None = Query(None, ge=-180, le=180, description="West bound of viewport"),
    lng_max: float | None = Query(None, ge=-180, le=180, description="East bound of viewport"),
    region: str | None = Query(None, description="e.g. south_asia, north_america, europe"),
    country_code: str | None = Query(None, description="ISO-2 country code: IN, AE, US..."),
    role: str | None = Query(None, description="Role category: engineering, design, product..."),
    is_remote: bool | None = Query(None),
    response: Response = None,
    db: Session = Depends(get_db),
):
    """Return company map pins with coordinates and filtered job counts for the globe UI."""
    loc_counts_q = db.query(
        Job.company_id,
        Job.latitude,
        Job.longitude,
        Job.city,
        Job.country_code,
        Job.region,
        func.count(Job.id).label("loc_cnt"),
    ).filter(Job.is_active.is_(True), Job.latitude.isnot(None))

    loc_counts = loc_counts_q.group_by(
        Job.company_id, Job.latitude, Job.longitude, Job.city, Job.country_code, Job.region
    ).subquery("loc_counts")

    best_loc = (
        db.query(
            loc_counts.c.company_id,
            loc_counts.c.latitude,
            loc_counts.c.longitude,
            loc_counts.c.city,
            loc_counts.c.country_code,
            loc_counts.c.region,
        )
        .distinct(loc_counts.c.company_id)
        .order_by(loc_counts.c.company_id, loc_counts.c.loc_cnt.desc())
        .subquery("best_loc")
    )

    resolved_lat = func.coalesce(Company.latitude, best_loc.c.latitude)
    resolved_lng = func.coalesce(Company.longitude, best_loc.c.longitude)
    resolved_city = func.coalesce(Company.city, best_loc.c.city)
    resolved_cc = func.coalesce(Company.country_code, best_loc.c.country_code)
    resolved_region = func.coalesce(Company.region, best_loc.c.region)

    filtered_jobs_q = db.query(Job.id, Job.company_id).filter(Job.is_active.is_(True))
    if role:
        filtered_jobs_q = filtered_jobs_q.filter(Job.role_category == role.lower())
    if is_remote is not None:
        filtered_jobs_q = filtered_jobs_q.filter(Job.is_remote.is_(is_remote))
    filtered_jobs = filtered_jobs_q.subquery("filtered_jobs")

    q = (
        db.query(
            Company.id,
            Company.name,
            Company.slug,
            resolved_city.label("city"),
            resolved_cc.label("country_code"),
            resolved_region.label("region"),
            resolved_lat.label("latitude"),
            resolved_lng.label("longitude"),
            Company.industry,
            Company.logo_url,
            func.count(filtered_jobs.c.id).label("job_count"),
        )
        .outerjoin(best_loc, best_loc.c.company_id == Company.id)
        .join(filtered_jobs, filtered_jobs.c.company_id == Company.id)
        .filter(
            Company.is_active.is_(True),
            resolved_lat.isnot(None),
        )
        .group_by(
            Company.id,
            best_loc.c.latitude,
            best_loc.c.longitude,
            best_loc.c.city,
            best_loc.c.country_code,
            best_loc.c.region,
        )
    )

    if lat_min is not None:
        q = q.filter(resolved_lat >= lat_min)
    if lat_max is not None:
        q = q.filter(resolved_lat <= lat_max)
    if lng_min is not None:
        q = q.filter(resolved_lng >= lng_min)
    if lng_max is not None:
        q = q.filter(resolved_lng <= lng_max)

    if region:
        q = q.filter(resolved_region == region.lower())
    if country_code:
        q = q.filter(resolved_cc == country_code.upper())

    rows = q.order_by(func.count(filtered_jobs.c.id).desc()).limit(500).all()

    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=30"

    return {
        "companies": [
            {
                "id": r.id,
                "name": r.name,
                "slug": r.slug,
                "city": r.city,
                "country_code": r.country_code,
                "region": r.region,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "industry": r.industry or [],
                "logo_url": r.logo_url,
                "job_count": r.job_count,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/cities", response_model=MapCitiesResponse)
def map_cities(
    lat_min: float | None = Query(None, ge=-90, le=90, description="South bound of viewport"),
    lat_max: float | None = Query(None, ge=-90, le=90, description="North bound of viewport"),
    lng_min: float | None = Query(None, ge=-180, le=180, description="West bound of viewport"),
    lng_max: float | None = Query(None, ge=-180, le=180, description="East bound of viewport"),
    region: str | None = Query(None),
    country_code: str | None = Query(None),
    role: str | None = Query(None, description="Count only jobs with this role category"),
    is_remote: bool | None = Query(None),
    response: Response = None,
    db: Session = Depends(get_db),
):
    """Return city cluster pins with aggregated job and company counts for the map UI."""
    job_agg_q = (
        db.query(
            City.id.label("city_id"),
            func.count(Job.id).label("job_count"),
            func.count(distinct(Job.company_id)).label("company_count"),
        )
        .join(Job, Job.city == City.name)
        .filter(Job.is_active.is_(True), City.latitude.isnot(None))
    )
    if role:
        job_agg_q = job_agg_q.filter(Job.role_category == role.lower())
    if is_remote is not None:
        job_agg_q = job_agg_q.filter(Job.is_remote.is_(is_remote))

    job_agg = job_agg_q.group_by(City.id).subquery("job_agg")

    city_q = (
        db.query(
            City,
            job_agg.c.job_count,
            job_agg.c.company_count,
        )
        .join(job_agg, job_agg.c.city_id == City.id)
        .filter(City.latitude.isnot(None), job_agg.c.job_count > 0)
    )

    if region:
        city_q = city_q.filter(City.region == region.lower())
    if country_code:
        city_q = city_q.filter(City.country_code == country_code.upper())

    if lat_min is not None:
        city_q = city_q.filter(City.latitude >= lat_min)
    if lat_max is not None:
        city_q = city_q.filter(City.latitude <= lat_max)
    if lng_min is not None:
        city_q = city_q.filter(City.longitude >= lng_min)
    if lng_max is not None:
        city_q = city_q.filter(City.longitude <= lng_max)

    rows = city_q.order_by(City.name).limit(500).all()

    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=120, stale-while-revalidate=30"

    return {
        "cities": [
            {
                "name": r.City.name,
                "slug": r.City.slug,
                "latitude": r.City.latitude,
                "longitude": r.City.longitude,
                "country_code": r.City.country_code,
                "region": r.City.region,
                "job_count": r.job_count,
                "company_count": r.company_count,
            }
            for r in rows
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
                "city": r.city,
                "country_code": r.country_code,
                "latitude": float(r.latitude),
                "longitude": float(r.longitude),
                "job_count": r.job_count,
            }
            for r in rows
        ]
    }
