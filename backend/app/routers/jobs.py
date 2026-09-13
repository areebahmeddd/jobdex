import base64
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, and_, cast, func, literal, null, or_, select, text, union_all
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, Job
from app.routers._builders import build_job_detail_response, build_job_response
from app.routers._filters import (
    FTS_VECTOR_SQL,
    LOCATION_DIMENSIONS,
    SORT_OPTIONS,
    SORT_RECENT,
    SORT_RELEVANCE,
    WORK_MODE_EXPR,
    JobFilters,
)
from app.schemas import (
    FacetBucket,
    JobDetailResponse,
    JobFacetsResponse,
    PaginatedJobsResponse,
)

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
    filters: JobFilters = Depends(),
    sort: str = Query(SORT_RECENT, description="recent (default) or relevance"),
    cursor: str | None = Query(None, description="Opaque cursor for keyset pagination"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return a paginated list of active jobs with optional filters and keyset or offset pagination."""
    base = (
        db.query(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .filter(Job.is_active.is_(True), Company.is_active.is_(True))
    )
    query = filters.apply(base)

    # Relevance needs a search term and cannot be keyset-paged, so it uses offsets.
    sort = sort if sort in SORT_OPTIONS else SORT_RECENT
    by_relevance = sort == SORT_RELEVANCE and filters.q is not None

    if by_relevance:
        rank_desc = text(
            f"ts_rank_cd({FTS_VECTOR_SQL}, websearch_to_tsquery('english', :rank_q)) DESC"
        ).bindparams(rank_q=filters.q)
        total = query.count()
        rows = (
            query.order_by(rank_desc, Job.posted_at.desc().nullslast(), Job.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return PaginatedJobsResponse(
            jobs=[build_job_response(j, c) for j, c in rows],
            total=total,
            limit=limit,
            offset=offset,
            sort=SORT_RELEVANCE,
            next_cursor=None,
        )

    if cursor:
        decoded = _decode_cursor(cursor)
        if decoded:
            cursor_posted_at, cursor_id = decoded
            if cursor_posted_at:
                # NULLS LAST puts undated jobs after the cursor, but posted_at <
                # :cursor never matches NULL, so they need admitting explicitly.
                query = query.filter(
                    or_(
                        Job.posted_at < cursor_posted_at,
                        and_(Job.posted_at == cursor_posted_at, Job.id < cursor_id),
                        Job.posted_at.is_(None),
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
        last = rows[-1][0]
        next_cursor = _encode_cursor(last.posted_at, last.id)

    return PaginatedJobsResponse(
        jobs=enriched,
        total=total,
        limit=limit,
        offset=offset if not cursor else None,
        sort=SORT_RECENT,
        next_cursor=next_cursor,
    )


# (column, dimensions its count ignores, parent column for hierarchical buckets)
_FACET_DIMENSIONS = {
    "ats_type": (Job.ats_type, frozenset({"ats_type"}), None),
    "role_category": (Job.role_category, frozenset({"role_category"}), None),
    "seniority": (Job.seniority, frozenset({"seniority"}), None),
    "job_type": (Job.job_type, frozenset({"job_type"}), None),
    "work_mode": (WORK_MODE_EXPR, frozenset({"work_mode"}), None),
    "country_code": (Job.country_code, LOCATION_DIMENSIONS, None),
    "city": (Job.city, LOCATION_DIMENSIONS, Job.country_code),
}
_FACET_TOTAL = "total"


def _listable_jobs(*columns):
    """Select over the jobs the list endpoint would return, so counts match the list."""
    return (
        select(*columns)
        .select_from(Job)
        .join(Company, Job.company_id == Company.id)
        .filter(Job.is_active.is_(True), Company.is_active.is_(True))
    )


def _facet_select(filters: JobFilters, dimension: str, column, skip, parent):
    """Count jobs per value of one dimension, ignoring that dimension's own selection."""
    parent_col = cast(parent, String) if parent is not None else cast(null(), String)
    stmt = _listable_jobs(
        literal(dimension).label("dimension"),
        cast(column, String).label("value"),
        parent_col.label("parent"),
        func.count(Job.id).label("count"),
    )
    stmt = filters.apply(stmt, skip=skip).group_by(column)
    return stmt.group_by(parent) if parent is not None else stmt


@router.get("/facets", response_model=JobFacetsResponse)
def job_facets(filters: JobFilters = Depends(), db: Session = Depends(get_db)):
    """Return per-option job counts for every filter dimension.

    Counts are disjunctive: a dimension ignores its own selection, so picking one
    option does not zero out the rest. All dimensions ship as one UNION ALL.
    """
    total_stmt = filters.apply(
        _listable_jobs(
            literal(_FACET_TOTAL).label("dimension"),
            cast(null(), String).label("value"),
            cast(null(), String).label("parent"),
            func.count(Job.id).label("count"),
        )
    )
    stmt = union_all(
        total_stmt,
        *(
            _facet_select(filters, dim, col, skip, parent)
            for dim, (col, skip, parent) in _FACET_DIMENSIONS.items()
        ),
    )

    buckets: dict[str, list[FacetBucket]] = {dim: [] for dim in _FACET_DIMENSIONS}
    total = 0
    for row in db.execute(stmt):
        if row.dimension == _FACET_TOTAL:
            total = row.count
        elif row.value is not None:
            buckets[row.dimension].append(
                FacetBucket(value=row.value, count=row.count, parent=row.parent)
            )

    for values in buckets.values():
        values.sort(key=lambda b: (-b.count, b.value))

    return JobFacetsResponse(total=total, **buckets)


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Return full details for a single job by its ID."""
    row = (
        db.query(Job, Company)
        .join(Company, Job.company_id == Company.id)
        .filter(Job.id == job_id, Job.is_active.is_(True), Company.is_active.is_(True))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return build_job_detail_response(row[0], row[1])
