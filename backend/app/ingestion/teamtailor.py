from datetime import datetime

import httpx2 as httpx

from app.config import settings
from app.ingestion.base import _DESCRIPTION_MAX_CHARS, _TECH_EXTRACT_CHARS, BaseIngester
from app.ingestion.normalizer import (
    classify_role,
    classify_seniority,
    extract_tech_stack,
    get_region_for_country,
    make_snippet,
    normalize_location,
    strip_html,
)
from app.models import Company, Job

# api.teamtailor.com/v1/jobs needs a per-company token, but every career site publishes
# the same postings as an unauthenticated JSON Feed, with a schema.org JobPosting under
# "_jobposting" carrying a structured postal address.
_FEED_URL = "https://{slug}.teamtailor.com/jobs.json"


class TeamtailorIngester(BaseIngester):
    ats_type = "teamtailor"

    async def fetch_raw(self, slug: str) -> list[dict]:
        """Fetch all published postings from a Teamtailor career site's public JSON Feed."""
        url = _FEED_URL.format(slug=slug)
        async with httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT,
            headers={"Accept": "application/json"},
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        # The feed is unpaginated and complete, so a missing item is a real closure.
        return [item for item in data.get("items", []) if item.get("id")]

    def extract_job_id(self, raw: dict) -> str:
        """Extract the Teamtailor posting ID from a raw feed item."""
        posting = raw.get("_jobposting") or {}
        identifier = posting.get("identifier") or {}
        # The schema.org identifier is the numeric posting ID; raw["id"] is a UUID.
        return str(identifier.get("value") or raw["id"])

    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        """Parse a raw Teamtailor feed item into an unsaved Job ORM object."""
        posting = raw.get("_jobposting") or {}
        title = raw.get("title") or posting.get("title") or ""

        if not company.website:
            org = posting.get("hiringOrganization") or {}
            if org.get("sameAs"):
                company.website = org["sameAs"]

        address = _first_address(posting)
        city_raw = (address.get("addressLocality") or "").strip()
        country_code_raw = (address.get("addressCountry") or "").strip().upper()
        # Most sites put the country name in addressRegion, not a subdivision.
        region_raw = (address.get("addressRegion") or "").strip()

        loc_parts = [p for p in (city_raw, region_raw or country_code_raw) if p]
        loc_raw = ", ".join(loc_parts)
        if not loc_raw:
            loc_raw = "Remote"

        html = raw.get("content_html") or posting.get("description") or ""
        plain = strip_html(html)

        loc = normalize_location(
            loc_raw,
            fallback_city=company.city,
            fallback_country_code=company.country_code or country_code_raw or None,
        )
        category, subcategory = classify_role(title, plain, "")
        seniority = classify_seniority(title)
        tech = extract_tech_stack(title, plain[:_TECH_EXTRACT_CHARS])
        posted_at = _parse_dt(raw.get("date_published") or posting.get("datePosted"))

        country_code = loc["country_code"] or country_code_raw or None
        region = loc["region"] or (get_region_for_country(country_code) if country_code else None)

        return Job(
            company_id=company.id,
            title=title,
            description=plain[:_DESCRIPTION_MAX_CHARS],
            description_snippet=make_snippet(plain),
            location_raw=loc_raw,
            # /cities joins on canonical names, so only those go in this column.
            city=loc["city"],
            country=loc["country"],
            country_code=country_code,
            region=region,
            latitude=loc["latitude"],
            longitude=loc["longitude"],
            is_remote=loc["is_remote"],
            remote_type=loc["remote_type"],
            # The feed carries no employment type, so fall back to the title.
            job_type="intern" if seniority == "intern" else "fulltime",
            seniority=seniority,
            role_category=category,
            role_subcategory=subcategory,
            tech_stack=tech,
            department="",
            source_url=raw.get("url", "") or "",
            ats_type=self.ats_type,
            ats_job_id=self.extract_job_id(raw),
            posted_at=posted_at,
            is_active=True,
        )


def _first_address(posting: dict) -> dict:
    """Return the first jobLocation postal address from a schema.org JobPosting."""
    locations = posting.get("jobLocation")
    if isinstance(locations, dict):
        locations = [locations]
    for place in locations or []:
        if isinstance(place, dict) and isinstance(place.get("address"), dict):
            return place["address"]
    return {}


def _parse_dt(raw: str | None) -> datetime | None:
    """Parse a Teamtailor ISO 8601 timestamp to a datetime, returning None on failure."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
