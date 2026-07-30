import asyncio
from datetime import UTC, datetime

import httpx2 as httpx
from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.ingestion.base import _DESCRIPTION_MAX_CHARS, _TECH_EXTRACT_CHARS, BaseIngester
from app.ingestion.normalizer import (
    classify_role,
    classify_seniority,
    extract_tech_stack,
    get_country_code_for_name,
    get_region_for_country,
    make_snippet,
    normalize_job_type,
    normalize_location,
    strip_html,
)
from app.models import Company, Job

# A board is addressed by three per-customer values that cannot be derived from the
# company name: tenant, data-centre number (wd1-wd12), and board name. They are packed
# into the slug as "tenant:wdN:board" so ats_slug stays a single string.
_LIST_URL = "https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{board}/jobs"
_DETAIL_URL = "https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{board}{path}"
_JOB_PAGE_URL = "https://{tenant}.{wd}.myworkdayjobs.com/{board}{path}"

# The API rejects limit > 20. Results are newest-first, so a board over the page cap
# keeps its freshest listings.
_PAGE_SIZE: int = 20
_MAX_PAGES: int = 100
_DETAIL_CONCURRENCY = 5

# Workday timeType -> JobDex job_type, read from the per-job detail fetch.
_TIME_TYPE_MAP: dict[str, str] = {
    "full time": "fulltime",
    "part time": "parttime",
    "fixed term": "contract",
    "intern": "intern",
}


class WorkdayIngester(BaseIngester):
    ats_type = "workday"

    async def fetch_raw(self, slug: str) -> list[dict]:
        """Fetch all postings from a Workday CXS board, enriched with per-job detail."""
        tenant, wd, board = _parse_slug(slug)
        list_url = _LIST_URL.format(tenant=tenant, wd=wd, board=board)

        postings: list[dict] = []
        seen_paths: set[str] = set()
        total = 0
        async with httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) as client:
            for page in range(_MAX_PAGES):
                response = await client.post(
                    list_url,
                    json={
                        "appliedFacets": {},
                        "limit": _PAGE_SIZE,
                        "offset": page * _PAGE_SIZE,
                        "searchText": "",
                    },
                )
                response.raise_for_status()
                data = response.json()
                batch = data.get("jobPostings", [])
                # total is populated on the first page only; later pages report 0.
                if page == 0:
                    total = data.get("total", 0)

                # An offset past the last page wraps around and re-serves page 0.
                fresh = [p for p in batch if p.get("externalPath") not in seen_paths]
                seen_paths.update(p.get("externalPath") for p in fresh)
                postings.extend(fresh)

                if not fresh or len(batch) < _PAGE_SIZE or (total and len(postings) >= total):
                    break
            else:
                logger.warning(
                    f"[{self.ats_type}] '{slug}' hit the {_MAX_PAGES}-page cap"
                    f" at {len(postings)} of {total} jobs; remainder skipped this run"
                )

            sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
            enriched = await asyncio.gather(
                *[_fetch_detail(client, tenant, wd, board, p, sem) for p in postings],
                return_exceptions=True,
            )

        return [item for item in enriched if isinstance(item, dict)]

    def extract_job_id(self, raw: dict) -> str:
        """Extract the stable Workday requisition ID from a raw posting dict."""
        # bulletFields[0] is the requisition number, e.g. "JR2020107". externalPath is
        # the fallback but embeds the title, so it changes when a posting is retitled.
        bullets = raw.get("bulletFields") or []
        if bullets and bullets[0]:
            return str(bullets[0])
        return str(raw["externalPath"])

    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        """Parse a raw Workday posting dict (list + detail merged) into an unsaved Job."""
        tenant, wd, board = _parse_slug(slug)
        title = raw.get("title", "")

        # locationsText reads "US, CA, Santa Clara", or "2 Locations" when a posting
        # spans sites. The detail location is cleaner, so prefer it.
        loc_raw = (raw.get("location") or raw.get("locationsText") or "").strip()
        loc_raw = _clean_location(loc_raw)

        html = raw.get("jobDescription", "") or ""
        plain = strip_html(html)

        loc = normalize_location(
            loc_raw,
            fallback_city=company.city,
            fallback_country_code=company.country_code,
        )

        # Workday reports the country as a display name, never an ISO code. Most board
        # cities are outside the city table, so without this most of a large board would
        # land with no country_code and no region.
        country = (raw.get("country") or {}).get("descriptor") or None
        country_code = loc["country_code"] or get_country_code_for_name(country)
        region = loc["region"] or (get_region_for_country(country_code) if country_code else None)

        category, subcategory = classify_role(title, plain, "")
        seniority = classify_seniority(title)
        tech = extract_tech_stack(title, plain[:_TECH_EXTRACT_CHARS])

        time_type = (raw.get("timeType") or "").strip().lower()
        job_type = _TIME_TYPE_MAP.get(time_type) or normalize_job_type(time_type)

        external_path = raw.get("externalPath", "") or ""
        source_url = raw.get("externalUrl") or _JOB_PAGE_URL.format(
            tenant=tenant, wd=wd, board=board, path=external_path
        )

        return Job(
            company_id=company.id,
            title=title,
            description=plain[:_DESCRIPTION_MAX_CHARS],
            description_snippet=make_snippet(plain),
            location_raw=loc_raw,
            city=loc["city"],
            country=loc["country"] or country,
            country_code=country_code,
            region=region,
            latitude=loc["latitude"],
            longitude=loc["longitude"],
            is_remote=loc["is_remote"],
            remote_type=loc["remote_type"],
            job_type=job_type or "fulltime",
            seniority=seniority,
            role_category=category,
            role_subcategory=subcategory,
            tech_stack=tech,
            department="",
            source_url=source_url,
            ats_type=self.ats_type,
            ats_job_id=self.extract_job_id(raw),
            # The list-level postedOn is a relative label ("Posted Today"), not a date.
            posted_at=_parse_date(raw.get("startDate")),
            is_active=True,
        )

    def _resolve_company(self, slug: str, db: Session) -> Company:
        """Resolve the Company for a composite slug, naming new stubs after the tenant."""
        company = (
            db.query(Company)
            .filter(Company.ats_slug == slug, Company.ats_type == self.ats_type)
            .first()
        )
        if company is None:
            tenant, _, _ = _parse_slug(slug)
            company = db.query(Company).filter(Company.slug == tenant).first()
            if company is None:
                logger.info(f"[{self.ats_type}] '{slug}' creating company stub")
                company = Company(
                    name=tenant.replace("-", " ").title(),
                    slug=tenant,
                    ats_type=self.ats_type,
                    ats_slug=slug,
                )
                db.add(company)
                db.flush()
        return company


async def _fetch_detail(
    client: httpx.AsyncClient,
    tenant: str,
    wd: str,
    board: str,
    posting: dict,
    sem: asyncio.Semaphore,
) -> dict:
    """Fetch per-job detail (description, timeType, real posted date) and merge it in."""
    path = posting.get("externalPath", "")
    if not path:
        return posting
    url = _DETAIL_URL.format(tenant=tenant, wd=wd, board=board, path=path)
    async with sem:
        try:
            response = await client.get(url)
            response.raise_for_status()
            info = response.json().get("jobPostingInfo") or {}
            return {**posting, **info}
        except Exception:
            return posting


def _parse_slug(slug: str) -> tuple[str, str, str]:
    """Split a "tenant:wdN:board" slug into its three parts.

    A bare tenant is accepted and defaults to the most common layout so a board can be
    registered by hand, but the full triple is what discover() seeds.
    """
    parts = slug.split(":")
    if len(parts) == 3:
        tenant, wd, board = (p.strip() for p in parts)
        if tenant and wd and board:
            return tenant, wd, board
    if len(parts) == 1 and parts[0]:
        return parts[0], "wd1", "External"
    raise ValueError(f"Workday slug must be 'tenant:wdN:board', got '{slug}'")


def _clean_location(raw: str) -> str:
    """Drop Workday's multi-site placeholder labels, which carry no geo information."""
    if not raw:
        return ""
    lowered = raw.lower()
    if lowered.endswith("locations") and lowered[:1].isdigit():
        return ""
    return raw


def _parse_date(raw: str | None) -> datetime | None:
    """Parse a Workday startDate (YYYY-MM-DD) into a UTC datetime, None on failure."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None
