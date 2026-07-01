from datetime import UTC, datetime

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

_BASE = "https://api.lever.co/v0/postings"


class LeverIngester(BaseIngester):
    ats_type = "lever"

    async def fetch_raw(self, slug: str) -> list[dict]:
        """Fetch raw job postings from the Lever public API for the given slug."""
        url = f"{_BASE}/{slug}?mode=json"
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get("postings", [])

    def extract_job_id(self, raw: dict) -> str:
        """Extract the Lever posting ID from a raw job dict."""
        return str(raw["id"])

    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        """Parse a raw Lever posting dict into an unsaved Job ORM object."""
        title = raw.get("text", "")
        cats = raw.get("categories") or {}
        loc_raw = cats.get("location", "") or ""
        department = cats.get("department", "") or ""
        team = cats.get("team", "") or ""
        commitment = cats.get("commitment", "") or ""

        html = raw.get("description", "") or raw.get("descriptionPlain", "") or ""
        plain = strip_html(html)

        loc = normalize_location(
            loc_raw,
            fallback_city=company.city,
            fallback_country_code=company.country_code,
        )
        full_dept = " ".join(filter(None, [department, team]))
        category, subcategory = classify_role(title, plain, full_dept)
        seniority = classify_seniority(title)
        job_type = normalize_job_type(commitment)
        tech = extract_tech_stack(title, plain[:_TECH_EXTRACT_CHARS])
        posted_at = _parse_ts(raw.get("createdAt"))

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
            source_url=raw.get("hostedUrl", "") or raw.get("applyUrl", ""),
            ats_type=self.ats_type,
            ats_job_id=str(raw["id"]),
            posted_at=posted_at,
            is_active=True,
        )


def _parse_ts(ts) -> datetime | None:
    """Convert a Lever millisecond Unix timestamp to a datetime object, returning None on failure."""
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts) / 1000, tz=UTC)
    except (TypeError, ValueError, OSError):
        return None
