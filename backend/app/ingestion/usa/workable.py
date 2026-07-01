import asyncio
from datetime import datetime

import httpx2 as httpx

from app.config import settings
from app.ingestion.base import _DESCRIPTION_MAX_CHARS, _TECH_EXTRACT_CHARS, BaseIngester
from app.ingestion.normalizer import (
    classify_role,
    classify_seniority,
    extract_tech_stack,
    make_snippet,
    normalize_job_type,
    normalize_location,
    strip_html,
)
from app.models import Company, Job

_LIST_URL = "https://apply.workable.com/api/v3/accounts/{slug}/jobs"
_DETAIL_URL = "https://apply.workable.com/api/v2/accounts/{slug}/jobs/{shortcode}"
_JOB_PAGE_URL = "https://apply.workable.com/{slug}/j/{shortcode}"

_DETAIL_CONCURRENCY = 5

_JOB_TYPE_MAP: dict[str, str] = {
    "full": "fulltime",
    "part": "parttime",
    "contract": "contract",
    "temporary": "temporary",
    "intern": "intern",
    "volunteer": "other",
    "other": "other",
}


class WorkableIngester(BaseIngester):
    ats_type = "workable"

    async def fetch_raw(self, slug: str) -> list[dict]:
        """Fetch all published non-internal job listings from Workable, enriched with per-job description."""
        url = _LIST_URL.format(slug=slug)
        jobs: list[dict] = []
        next_page: str | None = None
        async with httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT,
            headers={"Accept": "application/json"},
        ) as client:
            while True:
                payload: dict = {} if next_page is None else {"nextPage": next_page}
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                batch = [j for j in data.get("results", []) if not j.get("isInternal")]
                jobs.extend(batch)
                next_page = data.get("nextPage")
                if not next_page:
                    break

            sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
            enriched = await asyncio.gather(
                *[_fetch_detail(client, slug, job, sem) for job in jobs],
                return_exceptions=True,
            )

        return [item for item in enriched if isinstance(item, dict)]

    def extract_job_id(self, raw: dict) -> str:
        """Extract the Workable job shortcode from a raw job dict."""
        return str(raw["shortcode"])

    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        """Parse a raw Workable job dict (list + detail merged) into an unsaved Job ORM object."""
        title = raw.get("title", "")

        loc_data = raw.get("location") or {}
        city_raw = loc_data.get("city", "") or ""
        country_code_raw = (loc_data.get("countryCode", "") or "").upper()
        country_raw = loc_data.get("country", "") or ""
        region_raw = loc_data.get("region", "") or ""
        is_remote = raw.get("remote", False) or (raw.get("workplace", "") == "remote")
        is_hybrid = raw.get("workplace", "") == "hybrid"

        loc_parts = [p for p in [city_raw, region_raw] if p]
        loc_raw = ", ".join(loc_parts)
        if is_remote and not loc_raw:
            loc_raw = "Remote"
        elif (is_remote or is_hybrid) and "remote" not in loc_raw.lower():
            qualifier = "Remote" if is_remote else "Hybrid"
            loc_raw = f"{loc_raw} ({qualifier})" if loc_raw else qualifier

        department_list = raw.get("department") or []
        department = (
            department_list[0] if isinstance(department_list, list) and department_list else ""
        )

        job_type_raw = (raw.get("type", "") or "").lower()
        commitment = _JOB_TYPE_MAP.get(job_type_raw, job_type_raw)

        desc_html = (raw.get("description", "") or "") + (raw.get("requirements", "") or "")
        plain = strip_html(desc_html)

        loc = normalize_location(
            loc_raw,
            fallback_city=company.city,
            fallback_country_code=company.country_code or country_code_raw or None,
        )
        category, subcategory = classify_role(title, plain, department)
        seniority = classify_seniority(title)
        job_type = normalize_job_type(commitment)
        tech = extract_tech_stack(title, plain[:_TECH_EXTRACT_CHARS])
        posted_at = _parse_dt(raw.get("published", ""))
        shortcode = raw.get("shortcode", "")
        source_url = _JOB_PAGE_URL.format(slug=slug, shortcode=shortcode) if shortcode else ""

        return Job(
            company_id=company.id,
            title=title,
            description=plain[:_DESCRIPTION_MAX_CHARS],
            description_snippet=make_snippet(plain),
            location_raw=loc_raw,
            city=loc["city"],
            country=loc["country"] or country_raw or None,
            country_code=loc["country_code"] or country_code_raw or None,
            region=loc["region"],
            latitude=loc["latitude"],
            longitude=loc["longitude"],
            is_remote=is_remote or loc["is_remote"],
            remote_type=loc["remote_type"],
            job_type=job_type or "fulltime",
            seniority=seniority,
            role_category=category,
            role_subcategory=subcategory,
            tech_stack=tech,
            department=department,
            source_url=source_url,
            ats_type=self.ats_type,
            ats_job_id=shortcode,
            posted_at=posted_at,
            is_active=True,
        )


async def _fetch_detail(
    client: httpx.AsyncClient, slug: str, job: dict, sem: asyncio.Semaphore
) -> dict:
    """Fetch per-job detail (description, requirements) and merge into the list-level job dict."""
    shortcode = job.get("shortcode", "")
    url = _DETAIL_URL.format(slug=slug, shortcode=shortcode)
    async with sem:
        try:
            response = await client.get(url)
            response.raise_for_status()
            detail = response.json()
            return {**job, **detail}
        except Exception:
            return job


def _parse_dt(raw: str | None) -> datetime | None:
    """Parse a Workable ISO 8601 published string to a datetime object, returning None on failure."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
