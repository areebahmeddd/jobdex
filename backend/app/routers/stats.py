from fastapi import APIRouter, Depends, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import City, Company, Job
from app.schemas import StatsResponse

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def get_stats(response: Response = None, db: Session = Depends(get_db)):
    """Return aggregate platform statistics across companies, jobs, cities, and ATS providers."""
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    total_companies = db.query(func.count(Company.id)).scalar() or 0
    total_jobs = db.query(func.count(Job.id)).scalar() or 0
    active_jobs = db.query(func.count(Job.id)).filter(Job.is_active.is_(True)).scalar() or 0
    total_cities = db.query(func.count(City.id)).scalar() or 0

    cities_with_jobs = (
        db.query(func.count(func.distinct(Job.city)))
        .filter(Job.is_active.is_(True), Job.city.isnot(None))
        .scalar()
    ) or 0

    role_rows = (
        db.query(Job.role_category, func.count(Job.id))
        .filter(Job.is_active.is_(True), Job.role_category.isnot(None))
        .group_by(Job.role_category)
        .order_by(func.count(Job.id).desc())
        .all()
    )
    role_categories = {r[0]: r[1] for r in role_rows}

    city_rows = (
        db.query(Job.city, func.count(Job.id))
        .filter(Job.is_active.is_(True), Job.city.isnot(None))
        .group_by(Job.city)
        .order_by(func.count(Job.id).desc())
        .limit(10)
        .all()
    )
    top_cities = [{"city": r[0], "job_count": r[1]} for r in city_rows]

    region_rows = (
        db.query(Job.region, func.count(Job.id))
        .filter(Job.is_active.is_(True), Job.region.isnot(None))
        .group_by(Job.region)
        .order_by(func.count(Job.id).desc())
        .all()
    )
    top_regions = [{"region": r[0], "job_count": r[1]} for r in region_rows]

    ats_rows = (
        db.query(Company.ats_type, func.count(Company.id))
        .filter(Company.ats_type.isnot(None))
        .group_by(Company.ats_type)
        .all()
    )
    ats_breakdown = {r[0]: r[1] for r in ats_rows}

    return StatsResponse(
        total_companies=total_companies,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_cities=total_cities,
        cities_with_jobs=cities_with_jobs,
        role_categories=role_categories,
        top_cities=top_cities,
        top_regions=top_regions,
        ats_breakdown=ats_breakdown,
    )
