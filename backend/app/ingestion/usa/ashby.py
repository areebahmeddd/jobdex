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

_REST_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


class AshbyIngester(BaseIngester):
    ats_type = "ashby"

    async def fetch_raw(self, slug: str) -> list[dict]:
        """Fetch raw job listings from the Ashby posting API for the given slug."""
        url = _REST_URL.format(slug=slug)
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            data = response.json()
        return data.get("jobs") or []

    def extract_job_id(self, raw: dict) -> str:
        """Extract the Ashby job ID from a raw job dict."""
        return str(raw["id"])

    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        """Parse a raw Ashby job dict into an unsaved Job ORM object."""
        title = raw.get("title", "")

        loc_raw = raw.get("location", "") or ""
        is_remote_flag: bool = raw.get("isRemote", False) or False

        if is_remote_flag and not loc_raw:
            loc_raw = "Remote"
        elif is_remote_flag and "remote" not in loc_raw.lower():
            loc_raw = f"{loc_raw} (Remote)"

        department = raw.get("department", "") or ""
        team = raw.get("team", "") or ""
        full_dept = " ".join(filter(None, [department, team]))

        commitment = raw.get("employmentType", "") or ""
        html = raw.get("descriptionHtml", "") or ""
        plain = strip_html(html)

        loc = normalize_location(
            loc_raw,
            fallback_city=company.city,
            fallback_country_code=company.country_code,
        )
        category, subcategory = classify_role(title, plain, full_dept)
        seniority = classify_seniority(title)
        job_type = normalize_job_type(commitment)
        tech = extract_tech_stack(title, plain[:_TECH_EXTRACT_CHARS])
        posted_at = _parse_published(raw.get("publishedAt"))

        source_url = raw.get("applyUrl", "") or raw.get("jobUrl", "")
        if not source_url:
            source_url = f"https://jobs.ashbyhq.com/{slug}/{raw['id']}"

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
            is_remote=loc["is_remote"],
            remote_type=loc["remote_type"],
            job_type=job_type or "fulltime",
            seniority=seniority,
            role_category=category,
            role_subcategory=subcategory,
            tech_stack=tech,
            department=full_dept,
            source_url=source_url,
            ats_type=self.ats_type,
            ats_job_id=str(raw["id"]),
            posted_at=posted_at,
            is_active=True,
        )


def _parse_published(raw: str | None) -> datetime | None:
    """Parse an Ashby ISO 8601 publishedAt string to a datetime object, returning None on failure."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
