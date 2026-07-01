from datetime import datetime

import httpx2 as httpx

from app.config import settings
from app.ingestion.base import _TECH_EXTRACT_CHARS, BaseIngester
from app.ingestion.normalizer import (
    classify_role,
    classify_seniority,
    extract_tech_stack,
    normalize_job_type,
    normalize_location,
)
from app.models import Company, Job

_BASE = "https://api.smartrecruiters.com/v1/companies"
_PAGE_SIZE = 100

_EXP_LEVEL_MAP: dict[str, str] = {
    "internship": "intern",
    "entry level": "junior",
    "associate": "junior",
    "mid-senior level": "senior",
    "director": "director",
    "executive": "executive",
}


class SmartRecruitersIngester(BaseIngester):
    ats_type = "smartrecruiters"

    async def fetch_raw(self, slug: str) -> list[dict]:
        """Fetch all published job postings from the SmartRecruiters public API for the given slug."""
        url = f"{_BASE}/{slug}/postings"
        jobs: list[dict] = []
        offset = 0
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
            while True:
                response = await client.get(url, params={"limit": _PAGE_SIZE, "offset": offset})
                response.raise_for_status()
                data = response.json()
                batch = data.get("content", [])
                jobs.extend(batch)
                if not batch or len(jobs) >= data.get("totalFound", 0):
                    break
                offset += _PAGE_SIZE
        return jobs

    def extract_job_id(self, raw: dict) -> str:
        """Extract the SmartRecruiters posting ID from a raw job dict."""
        return str(raw["id"])

    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        """Parse a raw SmartRecruiters posting dict into an unsaved Job ORM object."""
        title = raw.get("name", "")

        loc_data = raw.get("location") or {}
        city_raw = loc_data.get("city", "") or ""
        country_code_raw = (loc_data.get("country") or "").upper()
        is_remote = bool(loc_data.get("remote", False))
        region_code = loc_data.get("regionCode", "") or ""

        loc_parts = [p for p in [city_raw, region_code] if p]
        loc_raw = ", ".join(loc_parts)
        if is_remote and not loc_raw:
            loc_raw = "Remote"
        elif is_remote and "remote" not in loc_raw.lower():
            loc_raw = f"{loc_raw} (Remote)"

        department = (raw.get("department") or {}).get("label", "") or ""
        function_ = (raw.get("function") or {}).get("label", "") or ""
        full_dept = " ".join(filter(None, [department, function_]))

        commitment = (raw.get("typeOfEmployment") or {}).get("label", "") or ""
        exp_label = ((raw.get("experienceLevel") or {}).get("label", "") or "").lower()

        loc = normalize_location(
            loc_raw,
            fallback_city=company.city,
            fallback_country_code=company.country_code or country_code_raw or None,
        )

        category, subcategory = classify_role(title, "", full_dept)
        title_seniority = classify_seniority(title)
        seniority = (
            title_seniority if title_seniority != "mid" else (_EXP_LEVEL_MAP.get(exp_label, "mid"))
        )
        job_type = normalize_job_type(commitment)
        tech = extract_tech_stack(title, ""[:_TECH_EXTRACT_CHARS])
        posted_at = _parse_dt(raw.get("releasedDate", ""))

        return Job(
            company_id=company.id,
            title=title,
            description="",
            description_snippet="",
            location_raw=loc_raw,
            city=loc["city"],
            country=loc["country"],
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
            department=full_dept,
            source_url=raw.get("ref", ""),
            ats_type=self.ats_type,
            ats_job_id=str(raw["id"]),
            posted_at=posted_at,
            is_active=True,
        )


def _parse_dt(raw: str) -> datetime | None:
    """Parse a SmartRecruiters ISO 8601 releasedDate string to a datetime, returning None on failure."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
