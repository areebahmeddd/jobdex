import base64
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.normalizer import canonicalize_city
from app.models import Company, Job
from app.routers._builders import build_job_detail_response, build_job_response
from app.schemas import JobDetailResponse, PaginatedJobsResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _encode_cursor(posted_at: datetime | None, job_id: str) -> str:
    """Encode a keyset pagination cursor from a posted_at datetime and job ID."""
    payload = {"p": posted_at.isoformat() if posted_at else "", "i": job_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime | None, str] | None:
    """Decode a keyset pagination cursor, returning (posted_at, job_id) or None if invalid."""
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor).decode())
        posted_at = datetime.fromisoformat(payload["p"]) if payload["p"] else None
        return posted_at, payload["i"]
    except Exception:
        return None


@router.get("", response_model=PaginatedJobsResponse)
def list_jobs(
    city: str | None = Query(None),
    country_code: str | None = Query(None),
    region: str | None = Query(None, description="e.g. south_asia, middle_east, europe"),
    role_category: str | None = Query(None),
    role_subcategory: str | None = Query(None),
    seniority: str | None = Query(None),
    is_remote: bool | None = Query(None),
    q: str | None = Query(None, description="Full-text search on title, snippet, and role"),
    cursor: str | None = Query(None, description="Opaque cursor for keyset pagination"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return a paginated list of active jobs with optional filters and keyset or offset pagination."""
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
        query = query.filter(
            text(
                "to_tsvector('english',"
                " coalesce(jobs.title,'') || ' ' ||"
                " coalesce(jobs.description_snippet,'') || ' ' ||"
                " coalesce(jobs.role_category,''))"
                " @@ websearch_to_tsquery('english', :q)"
            ).bindparams(q=q)
        )

    if cursor:
        decoded = _decode_cursor(cursor)
        if decoded:
            cursor_posted_at, cursor_id = decoded
            if cursor_posted_at:
                query = query.filter(
                    or_(
                        Job.posted_at < cursor_posted_at,
                        and_(Job.posted_at == cursor_posted_at, Job.id < cursor_id),
                    )
                )
            else:
                query = query.filter(and_(Job.posted_at.is_(None), Job.id < cursor_id))
        rows = query.order_by(Job.posted_at.desc().nullslast(), Job.id.desc()).limit(limit).all()
        total = None  # not computed for cursor pages
    else:
        total = query.count()
        rows = (
            query.order_by(Job.posted_at.desc().nullslast(), Job.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    enriched = [build_job_response(j, c) for j, c in rows]

    next_cursor = None
    if len(enriched) == limit:
        last = rows[-1][0]  # Job object
        next_cursor = _encode_cursor(last.posted_at, last.id)

    return PaginatedJobsResponse(
        jobs=enriched,
        total=total,
        limit=limit,
        offset=offset if not cursor else None,
        next_cursor=next_cursor,
    )


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Return full details for a single job by its ID."""
    row = (
        db.query(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .filter(Job.id == job_id, Job.is_active.is_(True))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return build_job_detail_response(row[0], row[1])
