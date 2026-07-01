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

_LIST_URL = "https://api.pyjamahr.com/api/career/jobs/"
_DETAIL_URL = "https://api.pyjamahr.com/api/career/jobs/{job_id}/"
_JOB_PAGE_URL = "https://jobs.pyjamahr.com/{slug}/{job_slug}"

_DETAIL_CONCURRENCY = 5

_REMOTE_WORKPLACE_TYPES: frozenset[str] = frozenset({"REMOTE"})
_HYBRID_WORKPLACE_TYPES: frozenset[str] = frozenset({"HYBRID"})


class PyjamaHRIngester(BaseIngester):
    ats_type = "pyjamahr"

    async def fetch_raw(self, slug: str) -> list[dict]:
        """Fetch all published job listings from PyjamaHR, enriched with per-job detail data."""
        jobs: list[dict] = []
        page = 1
        async with httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT,
            headers={"Accept": "application/json"},
        ) as client:
            while True:
                response = await client.get(_LIST_URL, params={"company_slug": slug, "page": page})
                response.raise_for_status()
                data = response.json()
                batch = data.get("results", [])
                jobs.extend(batch)
                if not data.get("next") or not batch:
                    break
                page += 1

            sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
            enriched = await asyncio.gather(
                *[_fetch_detail(client, slug, job, sem) for job in jobs],
                return_exceptions=True,
            )

        return [item for item in enriched if isinstance(item, dict)]

    def extract_job_id(self, raw: dict) -> str:
        """Extract the PyjamaHR job ID from a raw job dict."""
        return str(raw["id"])

    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        """Parse a raw PyjamaHR job dict (list + detail merged) into an unsaved Job ORM object."""
        title = raw.get("title", "")

        loc_raw = raw.get("location", "") or ""
        workplace_type = raw.get("workplace_type", "ON_SITE") or "ON_SITE"
        is_remote = raw.get("remote", False) or (workplace_type in _REMOTE_WORKPLACE_TYPES)
        is_hybrid = workplace_type in _HYBRID_WORKPLACE_TYPES

        if is_remote and not loc_raw:
            loc_raw = "Remote"
        elif (is_remote or is_hybrid) and "remote" not in loc_raw.lower():
            qualifier = "Remote" if is_remote else "Hybrid"
            loc_raw = f"{loc_raw} ({qualifier})" if loc_raw else qualifier

        department = raw.get("department_name", "") or ""

        seniority_list = raw.get("seniority") or []
        ats_seniority = seniority_list[0] if seniority_list else ""
        seniority = classify_seniority(title) or ats_seniority or "mid"

        commitment = (raw.get("job_type", "") or "").lower().replace("_", "-").replace("-based", "")
        html = raw.get("description", "") or ""
        plain = strip_html(html)

        skill_list = raw.get("skill") or []
        skill_text = " ".join(skill_list)

        loc = normalize_location(
            loc_raw,
            fallback_city=company.city,
            fallback_country_code=company.country_code,
        )
        category, subcategory = classify_role(title, plain, department)
        job_type = normalize_job_type(commitment)
        tech = extract_tech_stack(title, f"{plain[:_TECH_EXTRACT_CHARS]} {skill_text}")
        posted_at = _parse_dt(raw.get("created_at", ""))

        job_slug = raw.get("slug", "")
        source_url = _JOB_PAGE_URL.format(slug=slug, job_slug=job_slug) if job_slug else ""

        return Job(
            company_id=company.id,
            title=title,
            description=plain[:_DESCRIPTION_MAX_CHARS],
            description_snippet=make_snippet(plain),
            location_raw=loc_raw,
            city=loc["city"],
            country=loc["country"],
            country_code=loc["country_code"],
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
            ats_job_id=str(raw["id"]),
            posted_at=posted_at,
            is_active=True,
        )


async def _fetch_detail(
    client: httpx.AsyncClient,
    slug: str,
    job: dict,
    sem: asyncio.Semaphore,
) -> dict:
    """Fetch the full job detail from PyjamaHR and merge it into the list-level job dict."""
    job_id = job["id"]
    url = _DETAIL_URL.format(job_id=job_id)
    async with sem:
        try:
            response = await client.get(url, params={"company_slug": slug})
            if response.status_code == 200:
                detail = response.json()
                return {**job, **detail}
        except httpx.RequestError:
            pass
    return job


def _parse_dt(raw: str) -> datetime | None:
    """Parse a PyjamaHR ISO 8601 created_at string to a datetime, returning None on failure."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
