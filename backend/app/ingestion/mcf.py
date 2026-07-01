from datetime import UTC, datetime

import httpx2 as httpx

from app.config import settings
from app.ingestion.base import _DESCRIPTION_MAX_CHARS, _TECH_EXTRACT_CHARS, BaseIngester
from app.ingestion.normalizer import (
    classify_role,
    classify_seniority,
    extract_tech_stack,
    get_region_for_country,
    make_snippet,
    normalize_job_type,
    strip_html,
)
from app.models import Company, Job

_LIST_URL = "https://api.mycareersfuture.gov.sg/v2/jobs"
_PAGE_SIZE: int = 100

# MCF employmentType string -> JobDex job_type
_EMPLOYMENT_TYPE_MAP: dict[str, str] = {
    "Full Time": "fulltime",
    "Part Time": "parttime",
    "Contract": "contract",
    "Internship": "intern",
    "Temporary": "contract",
    "Freelance": "contract",
}

# MCF positionLevel string -> seniority (used as ATS hint; title classification takes priority)
_POSITION_LEVEL_MAP: dict[str, str] = {
    "Fresh/entry level": "junior",
    "Junior Executive": "junior",
    "Non-executive": "mid",
    "Executive": "mid",
    "Professional": "mid",
    "Senior Executive": "senior",
    "Senior Management": "senior",
    "Manager": "manager",
    "Senior Manager": "manager",
    "Director": "director",
    "C-Suite": "executive",
}


class MCFIngester(BaseIngester):
    ats_type = "mcf"

    async def fetch_raw(self, slug: str) -> list[dict]:
        """Fetch all open MCF job listings for the given company name slug."""
        jobs: list[dict] = []
        page = 0
        async with httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT,
            headers={"Accept": "application/json"},
        ) as client:
            while True:
                response = await client.get(
                    _LIST_URL,
                    params={"company": slug, "limit": _PAGE_SIZE, "page": page},
                )
                response.raise_for_status()
                data = response.json()
                batch = data.get("results", [])
                jobs.extend(batch)
                total = data.get("total", 0)
                if not batch or len(jobs) >= total:
                    break
                page += 1
        return jobs

    def extract_job_id(self, raw: dict) -> str:
        """Extract the MCF job UUID from a raw job dict."""
        return str(raw["uuid"])

    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        """Parse a raw MCF job dict into an unsaved Job ORM object."""
        title = raw.get("title", "")

        address = raw.get("address") or {}
        is_overseas = address.get("isOverseas", False)

        if is_overseas:
            overseas = address.get("overseasCountry") or {}
            country_name = (
                overseas.get("countryName", "") if isinstance(overseas, dict) else str(overseas)
            )
            country_code = (
                overseas.get("countryCode", "") if isinstance(overseas, dict) else ""
            ).upper() or None
            loc_raw = country_name or "Overseas"
            city = None
            country = country_name or None
            region = get_region_for_country(country_code) if country_code else None
            lat = None
            lng = None
        else:
            street = address.get("street", "") or ""
            postal = address.get("postalCode", "") or ""
            loc_raw = (
                f"{street}, Singapore {postal}".strip(", ")
                if street
                else f"Singapore {postal}".strip()
            )
            city = "Singapore"
            country = "Singapore"
            country_code = "SG"
            region = get_region_for_country("SG")
            lat = address.get("lat") or None
            lng = address.get("lng") or None

        cats = raw.get("categories") or []
        department = cats[0].get("category", "") if cats else ""

        emp_types = raw.get("employmentTypes") or []
        raw_emp_type = emp_types[0].get("employmentType", "") if emp_types else ""
        job_type = _EMPLOYMENT_TYPE_MAP.get(raw_emp_type) or normalize_job_type(raw_emp_type)

        pos_levels = raw.get("positionLevels") or []
        raw_level = pos_levels[0].get("position", "") if pos_levels else ""
        ats_seniority = _POSITION_LEVEL_MAP.get(raw_level, "")

        html = raw.get("description", "") or ""
        plain = strip_html(html)

        skills_list = raw.get("skills") or []
        skill_text = " ".join(s.get("skill", "") for s in skills_list if s.get("skill"))

        category, subcategory = classify_role(title, plain, department)
        title_seniority = classify_seniority(title)
        seniority = title_seniority if title_seniority != "mid" else (ats_seniority or "mid")
        tech = extract_tech_stack(title, f"{plain[:_TECH_EXTRACT_CHARS]} {skill_text}")

        meta = raw.get("metadata") or {}
        posted_at = _parse_date(meta.get("newPostingDate"))
        source_url = meta.get("jobDetailsUrl", "") or ""

        return Job(
            company_id=company.id,
            title=title,
            description=plain[:_DESCRIPTION_MAX_CHARS],
            description_snippet=make_snippet(plain),
            location_raw=loc_raw,
            city=city,
            country=country,
            country_code=country_code,
            region=region,
            latitude=lat,
            longitude=lng,
            is_remote=False,
            remote_type=None,
            job_type=job_type or "fulltime",
            seniority=seniority,
            role_category=category,
            role_subcategory=subcategory,
            tech_stack=tech,
            department=department,
            source_url=source_url,
            ats_type=self.ats_type,
            ats_job_id=str(raw["uuid"]),
            posted_at=posted_at,
            is_active=True,
        )


def _parse_date(raw: str | None) -> datetime | None:
    """Parse an MCF posting date string (YYYY-MM-DD) into a UTC midnight datetime."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None
