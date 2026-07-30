import asyncio
from datetime import datetime

import httpx2 as httpx

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

_LIST_URL = "https://api.rippling.com/platform/api/ats/v1/board/{slug}/jobs"
_DETAIL_URL = "https://api.rippling.com/platform/api/ats/v1/board/{slug}/jobs/{uuid}"
_JOB_PAGE_URL = "https://ats.rippling.com/{slug}/jobs/{uuid}"

_DETAIL_CONCURRENCY = 5

# employmentType.label holds the machine code and employmentType.id the human label,
# the reverse of the usual convention.
_EMPLOYMENT_TYPE_MAP: dict[str, str] = {
    "SALARIED_FT": "fulltime",
    "SALARIED_PT": "parttime",
    "HOURLY_FT": "fulltime",
    "HOURLY_PT": "parttime",
    "CONTRACTOR": "contract",
    "TEMP": "temporary",
    "INTERN": "intern",
}


class RipplingIngester(BaseIngester):
    ats_type = "rippling"

    async def fetch_raw(self, slug: str) -> list[dict]:
        """Fetch all open jobs from a Rippling ATS board, enriched with per-job detail."""
        url = _LIST_URL.format(slug=slug)
        async with httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT,
            headers={"Accept": "application/json"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            # The board endpoint returns a bare list and is not paginated.
            jobs = data if isinstance(data, list) else data.get("items", [])

            sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
            enriched = await asyncio.gather(
                *[_fetch_detail(client, slug, job, sem) for job in jobs],
                return_exceptions=True,
            )

        return [item for item in enriched if isinstance(item, dict)]

    def extract_job_id(self, raw: dict) -> str:
        """Extract the Rippling job UUID from a raw job dict."""
        return str(raw["uuid"])

    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        """Parse a raw Rippling job dict (list + detail merged) into an unsaved Job."""
        title = (raw.get("name") or "").strip()

        board = raw.get("board") or {}
        logo = (board.get("logo") or {}).get("url")
        if logo and not company.logo_url:
            company.logo_url = logo

        # workLocations (detail) is a list of strings; workLocation (list) is an object.
        locations = raw.get("workLocations") or []
        if locations:
            loc_raw = str(locations[0])
        else:
            loc_raw = ((raw.get("workLocation") or {}).get("label") or "").strip()

        department_raw = raw.get("department") or {}
        # Detail nests {"name": ...}; the list payload nests {"label": ...}.
        department = department_raw.get("name") or department_raw.get("label") or ""

        description = raw.get("description")
        if isinstance(description, dict):
            html = (description.get("role") or "") + (description.get("company") or "")
        else:
            html = description or ""
        plain = strip_html(html)

        loc = normalize_location(
            loc_raw,
            fallback_city=company.city,
            fallback_country_code=company.country_code,
        )
        category, subcategory = classify_role(title, plain, department)
        seniority = classify_seniority(title)
        tech = extract_tech_stack(title, plain[:_TECH_EXTRACT_CHARS])

        emp = raw.get("employmentType") or {}
        emp_code = (emp.get("label") or "").strip().upper()
        job_type = _EMPLOYMENT_TYPE_MAP.get(emp_code) or normalize_job_type(
            (emp.get("id") or "").lower()
        )

        # Locations read "City, Country", so the tail still gives a country when the
        # city is outside the city table.
        country_code = loc["country_code"] or _country_code_from_tail(loc_raw)
        region = loc["region"] or (get_region_for_country(country_code) if country_code else None)

        uuid = str(raw["uuid"])
        return Job(
            company_id=company.id,
            title=title,
            description=plain[:_DESCRIPTION_MAX_CHARS],
            description_snippet=make_snippet(plain),
            location_raw=loc_raw,
            city=loc["city"],
            country=loc["country"],
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
            department=department,
            source_url=raw.get("url") or _JOB_PAGE_URL.format(slug=slug, uuid=uuid),
            ats_type=self.ats_type,
            ats_job_id=uuid,
            posted_at=_parse_dt(raw.get("createdOn")),
            is_active=True,
        )


async def _fetch_detail(
    client: httpx.AsyncClient, slug: str, job: dict, sem: asyncio.Semaphore
) -> dict:
    """Fetch per-job detail (description, employment type, posted date) and merge it in."""
    uuid = job.get("uuid", "")
    if not uuid:
        return job
    url = _DETAIL_URL.format(slug=slug, uuid=uuid)
    async with sem:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return {**job, **response.json()}
        except Exception:
            return job


def _country_code_from_tail(location: str) -> str | None:
    """Return the ISO-2 code if the last comma-separated segment names a country."""
    if not location:
        return None
    return get_country_code_for_name(location.rsplit(",", 1)[-1])


def _parse_dt(raw: str | None) -> datetime | None:
    """Parse a Rippling ISO 8601 createdOn string to a datetime, None on failure."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
