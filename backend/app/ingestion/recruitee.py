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

_LIST_URL = "https://{slug}.recruitee.com/api/offers/"

_JOB_TYPE_MAP: dict[str, str] = {
    "fulltime": "fulltime",
    "fulltime_fixed_term": "fulltime",
    "parttime": "parttime",
    "contract": "contract",
    "internship": "intern",
    "temporary": "temporary",
    "freelance": "contract",
}

_EXP_CODE_MAP: dict[str, str] = {
    "entry_level": "junior",
    "mid_level": "mid",
    "senior": "senior",
    "director": "director",
    "executive": "executive",
    "internship": "intern",
}


class RecruiteeIngester(BaseIngester):
    ats_type = "recruitee"

    async def fetch_raw(self, slug: str) -> list[dict]:
        """Fetch all published job offers from a Recruitee company subdomain."""
        url = _LIST_URL.format(slug=slug)
        async with httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT,
            headers={"Accept": "application/json"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        return [o for o in data.get("offers", []) if o.get("status") == "published"]

    def extract_job_id(self, raw: dict) -> str:
        """Extract the Recruitee offer ID from a raw offer dict."""
        return str(raw["id"])

    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        """Parse a raw Recruitee offer dict into an unsaved Job ORM object."""
        title = raw.get("title", "")

        loc_raw = raw.get("location", "") or ""
        city_raw = raw.get("city", "") or ""
        country_code_raw = (raw.get("country_code", "") or "").upper()
        country_raw = raw.get("country", "") or ""
        is_remote = raw.get("remote", False) or False
        is_hybrid = raw.get("hybrid", False) or False

        if not loc_raw:
            loc_parts = [p for p in [city_raw, country_raw] if p]
            loc_raw = ", ".join(loc_parts)
        if is_remote and not loc_raw:
            loc_raw = "Remote"
        elif (is_remote or is_hybrid) and "remote" not in loc_raw.lower():
            qualifier = "Remote" if is_remote else "Hybrid"
            loc_raw = f"{loc_raw} ({qualifier})" if loc_raw else qualifier

        department = raw.get("department", "") or ""

        emp_code = (raw.get("employment_type_code", "") or "").lower()
        commitment = _JOB_TYPE_MAP.get(emp_code, emp_code)

        desc_html = raw.get("description", "") or ""
        req_html = raw.get("requirements", "") or ""
        if not desc_html:
            translations = raw.get("translations") or {}
            lang_data = translations.get("en") or next(iter(translations.values()), {})
            desc_html = lang_data.get("description", "") or ""
            req_html = req_html or (lang_data.get("requirements", "") or "")
        plain = strip_html(desc_html + req_html)

        loc = normalize_location(
            loc_raw,
            fallback_city=company.city,
            fallback_country_code=company.country_code or country_code_raw or None,
        )
        category, subcategory = classify_role(title, plain, department)
        exp_code = (raw.get("experience_code", "") or "").lower()
        ats_seniority = _EXP_CODE_MAP.get(exp_code, "")
        title_seniority = classify_seniority(title)
        seniority = title_seniority if title_seniority != "mid" else (ats_seniority or "mid")
        job_type = normalize_job_type(commitment)
        tech = extract_tech_stack(title, plain[:_TECH_EXTRACT_CHARS])
        posted_at = _parse_dt(raw.get("published_at"))
        source_url = raw.get("careers_url", "") or ""

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
            ats_job_id=str(raw["id"]),
            posted_at=posted_at,
            is_active=True,
        )


def _parse_dt(raw: str | None) -> datetime | None:
    """Parse a Recruitee datetime string to a datetime object, returning None on failure."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S %Z").replace(tzinfo=UTC)
    except (ValueError, AttributeError):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
