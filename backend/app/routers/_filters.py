"""Job filter parsing and SQL application shared by every job-backed endpoint."""

import copy
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Query
from sqlalchemy import and_, case, or_, select, text
from sqlalchemy.orm import Query as OrmQuery

from app.ingestion.normalizer import canonicalize_city
from app.models import Company, Job

SORT_RECENT = "recent"
SORT_RELEVANCE = "relevance"
SORT_OPTIONS = (SORT_RECENT, SORT_RELEVANCE)

WORK_MODE_REMOTE = "remote"
WORK_MODE_HYBRID = "hybrid"
WORK_MODE_ONSITE = "onsite"
WORK_MODES = (WORK_MODE_REMOTE, WORK_MODE_HYBRID, WORK_MODE_ONSITE)

POSTED_WITHIN_MAX_DAYS = 365

# City and country are one choice in the UI, so a location facet skips both.
LOCATION_DIMENSIONS = frozenset({"city", "country_code"})

# Caps on user-supplied input before it reaches a query: the first two bound an
# IN clause, the third bounds the free-text search string.
_MAX_VALUES_PER_FILTER = 25
_MAX_VALUE_LENGTH = 100
_MAX_QUERY_LENGTH = 200

# Must match ix_jobs_fts_gin exactly for the index to serve both match and ranking.
FTS_VECTOR_SQL = (
    "to_tsvector('english',"
    " coalesce(jobs.title,'') || ' ' ||"
    " coalesce(jobs.description_snippet,'') || ' ' ||"
    " coalesce(jobs.role_category,''))"
)

# Only 'hybrid' is matched exactly, so an unknown remote_type still counts as remote.
WORK_MODE_EXPR = case(
    (Job.is_remote.is_(False), WORK_MODE_ONSITE),
    (Job.remote_type == WORK_MODE_HYBRID, WORK_MODE_HYBRID),
    else_=WORK_MODE_REMOTE,
)


# Empty value per dimension, used by JobFilters.without().
_CLEARED: dict[str, object] = {
    "city": None,
    "country_code": None,
    "region": None,
    "q": None,
    "is_remote": None,
    "posted_within": None,
    "role_category": [],
    "role_subcategory": [],
    "seniority": [],
    "job_type": [],
    "ats_type": [],
    "work_mode": [],
}


def _clean_multi(values: list[str] | None) -> list[str]:
    """Normalize, dedupe, and cap a repeated query parameter."""
    if not values:
        return []
    out: list[str] = []
    for raw in values:
        value = raw.strip().lower()[:_MAX_VALUE_LENGTH]
        if not value:
            continue
        if value not in out:
            out.append(value)
        if len(out) >= _MAX_VALUES_PER_FILTER:
            break
    return out


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so a literal query stays literal."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class JobFilters:
    """Query parameters shared by every job-backed endpoint."""

    def __init__(
        self,
        city: Annotated[
            str | None,
            Query(description="City name; aliases such as 'Bengaluru' or 'NYC' resolve"),
        ] = None,
        country_code: Annotated[str | None, Query(description="ISO-2 country code")] = None,
        region: Annotated[
            str | None, Query(description="e.g. south_asia, middle_east, europe")
        ] = None,
        role_category: Annotated[
            list[str] | None, Query(description="Repeatable: engineering, design, product...")
        ] = None,
        role: Annotated[
            list[str] | None,
            Query(description="Alias for role_category, kept for the map and search endpoints"),
        ] = None,
        role_subcategory: Annotated[
            list[str] | None, Query(description="Repeatable: backend, mobile, ux...")
        ] = None,
        seniority: Annotated[
            list[str] | None, Query(description="Repeatable: junior, mid, senior, staff...")
        ] = None,
        job_type: Annotated[
            list[str] | None, Query(description="Repeatable: fulltime, parttime, contract...")
        ] = None,
        ats_type: Annotated[
            list[str] | None,
            Query(description="Repeatable source filter: greenhouse, ycombinator, workday..."),
        ] = None,
        work_mode: Annotated[
            list[str] | None, Query(description="Repeatable: remote, hybrid, onsite")
        ] = None,
        is_remote: Annotated[
            bool | None, Query(description="Legacy two-state remote filter; prefer work_mode")
        ] = None,
        posted_within: Annotated[
            int | None,
            Query(
                ge=1,
                le=POSTED_WITHIN_MAX_DAYS,
                description="Only jobs with a known posted date within this many days",
            ),
        ] = None,
        q: Annotated[
            str | None, Query(description="Full-text search on title, snippet, and role")
        ] = None,
    ):
        raw_city = city.strip() if city else ""
        # Resolved once: canonicalize_city can fuzzy match, and /jobs/facets applies
        # the same filters eight times.
        self.city = (canonicalize_city(raw_city) or raw_city) if raw_city else None
        self.country_code = country_code.strip().upper() if country_code else None
        self.region = region.strip().lower() if region else None
        self.role_category = _clean_multi([*(role_category or []), *(role or [])])
        self.role_subcategory = _clean_multi(role_subcategory)
        self.seniority = _clean_multi(seniority)
        self.job_type = _clean_multi(job_type)
        self.ats_type = _clean_multi(ats_type)
        self.work_mode = [m for m in _clean_multi(work_mode) if m in WORK_MODES]
        self.is_remote = is_remote
        self.posted_within = posted_within
        # One cutoff per request, so every facet count describes the same window.
        self.posted_cutoff = (
            datetime.now(UTC) - timedelta(days=posted_within) if posted_within else None
        )
        query_text = q.strip()[:_MAX_QUERY_LENGTH] if q else ""
        self.q = query_text or None

    def without(self, *names: str) -> "JobFilters":
        """Return a copy with the named dimensions cleared."""
        clone = copy.copy(self)
        for name in names:
            setattr(clone, name, _CLEARED[name])
        return clone

    @property
    def has_job_scope(self) -> bool:
        """True if any filter narrows the job set."""
        return bool(
            self.city
            or self.country_code
            or self.region
            or self.role_category
            or self.role_subcategory
            or self.seniority
            or self.job_type
            or self.ats_type
            or self.work_mode
            or self.q
            or self.posted_within
            or self.is_remote is not None
        )

    def apply(self, query: OrmQuery, *, skip: frozenset[str] = frozenset()) -> OrmQuery:
        """Apply every active filter to a query already scoped to active jobs.

        `skip` omits dimensions so a facet count can ignore its own selection.
        """
        if self.city and "city" not in skip:
            query = query.filter(Job.city == self.city)
        if self.country_code and "country_code" not in skip:
            query = query.filter(Job.country_code == self.country_code)
        if self.region:
            query = query.filter(Job.region == self.region)
        if self.role_category and "role_category" not in skip:
            query = query.filter(Job.role_category.in_(self.role_category))
        if self.role_subcategory:
            query = query.filter(Job.role_subcategory.in_(self.role_subcategory))
        if self.seniority and "seniority" not in skip:
            query = query.filter(Job.seniority.in_(self.seniority))
        if self.job_type and "job_type" not in skip:
            query = query.filter(Job.job_type.in_(self.job_type))
        if self.ats_type and "ats_type" not in skip:
            query = query.filter(Job.ats_type.in_(self.ats_type))
        if "work_mode" not in skip:
            query = self._apply_work_mode(query)
        # Gated on posted_within so without("posted_within") clears the window too.
        if self.posted_within and self.posted_cutoff:
            query = query.filter(Job.posted_at >= self.posted_cutoff)
        if self.q:
            # A query matches a job's text or its company's name, so "Adobe" and
            # "devops" both list jobs on every surface.
            fts = text(f"{FTS_VECTOR_SQL} @@ websearch_to_tsquery('english', :fts_q)").bindparams(
                fts_q=self.q
            )
            named = select(Company.id).where(Company.name.ilike(f"%{_escape_like(self.q)}%"))
            query = query.filter(or_(fts, Job.company_id.in_(named)))
        return query

    def _apply_work_mode(self, query: OrmQuery) -> OrmQuery:
        """Apply the three-state work mode filter, falling back to the legacy boolean."""
        if self.work_mode:
            clauses = []
            if WORK_MODE_REMOTE in self.work_mode:
                clauses.append(
                    and_(
                        Job.is_remote.is_(True),
                        or_(Job.remote_type.is_(None), Job.remote_type != WORK_MODE_HYBRID),
                    )
                )
            if WORK_MODE_HYBRID in self.work_mode:
                clauses.append(and_(Job.is_remote.is_(True), Job.remote_type == WORK_MODE_HYBRID))
            if WORK_MODE_ONSITE in self.work_mode:
                clauses.append(Job.is_remote.is_(False))
            return query.filter(or_(*clauses))
        if self.is_remote is not None:
            return query.filter(Job.is_remote.is_(self.is_remote))
        return query
