import asyncio
from datetime import UTC, datetime

import httpx2 as httpx

from app.config import settings
from app.ingestion.base import _DESCRIPTION_MAX_CHARS, _TECH_EXTRACT_CHARS, BaseIngester
from app.ingestion.normalizer import (
    classify_role,
    classify_seniority,
    extract_tech_stack,
    make_snippet,
    normalize_location,
    strip_html,
)
from app.models import Company, Job

_API_BASE = "https://api.ycombinator.com/v0.1/companies"
_WAAS_BASE = "https://workatastartup.com/companies"
_DISCOVER_PAGE_DELAY = 0.2


class YCombinatorIngester(BaseIngester):
    ats_type = "ycombinator"

    async def fetch_raw(self, slug: str) -> list[dict]:
        """Fetch the YC company by slug and return it if actively hiring."""
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
            resp = await client.get(_API_BASE, params={"q": slug})
            resp.raise_for_status()
            data = resp.json()

        match = next((c for c in data.get("companies", []) if c.get("slug") == slug), None)
        if match is None or "isHiring" not in (match.get("badges") or []):
            return []

        return [match]

    def extract_job_id(self, raw: dict) -> str:
        """Use the YC numeric company ID as the stable job identifier."""
        return str(raw["id"])

    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        """Parse a raw YC API company dict into an unsaved Job ORM object."""
        if not company.logo_url and raw.get("smallLogoUrl"):
            company.logo_url = raw["smallLogoUrl"]
        if not company.website and raw.get("website"):
            company.website = raw["website"]
        if not company.description and raw.get("longDescription"):
            company.description = strip_html(raw["longDescription"])[:5_000]

        one_liner = (raw.get("oneLiner") or "").strip().rstrip(".")
        company_name = raw.get("name") or company.name or slug.replace("-", " ").title()
        title = one_liner if one_liner else f"Open positions at {company_name}"

        plain = strip_html(raw.get("longDescription") or "")

        yc_locations = raw.get("locations") or []
        loc_raw = yc_locations[0] if yc_locations else ""
        loc = normalize_location(
            loc_raw,
            fallback_city=company.city,
            fallback_country_code=company.country_code,
        )

        yc_regions = raw.get("regions") or []
        if any(r.lower() == "fully remote" for r in yc_regions) and not loc["is_remote"]:
            loc["is_remote"] = True
            loc["remote_type"] = "fully_remote"

        category, subcategory = classify_role(title, plain, "")
        seniority = classify_seniority(title)
        tech = extract_tech_stack(title, plain[:_TECH_EXTRACT_CHARS])

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
            job_type="fulltime",
            seniority=seniority,
            role_category=category,
            role_subcategory=subcategory,
            tech_stack=tech,
            department="",
            source_url=f"{_WAAS_BASE}/{slug}",
            ats_type=self.ats_type,
            ats_job_id=str(raw["id"]),
            posted_at=datetime.now(tz=UTC),
            is_active=True,
        )

    async def probe(self, slug: str) -> bool:
        """Return True only if the company exists in the YC database and is hiring."""
        try:
            return len(await self.fetch_raw(slug)) > 0
        except Exception:
            return False

    async def discover(self) -> list[Company]:
        """Paginate the YC API and return Company stubs for all currently hiring companies."""
        stubs: list[Company] = []
        page = 1
        total_pages = 1

        async with httpx.AsyncClient(timeout=30.0) as client:
            while page <= total_pages:
                resp = await client.get(
                    _API_BASE,
                    params={"isHiring": "true", "page": str(page)},
                )
                resp.raise_for_status()
                data = resp.json()
                total_pages = data.get("totalPages", 1)

                for yc in data.get("companies", []):
                    slug = yc.get("slug", "")
                    if not slug:
                        continue
                    locations = yc.get("locations") or []
                    loc = normalize_location(locations[0] if locations else "")
                    stubs.append(
                        Company(
                            name=yc.get("name") or slug.replace("-", " ").title(),
                            slug=slug,
                            logo_url=yc.get("smallLogoUrl"),
                            description=(yc.get("longDescription") or "")[:5_000] or None,
                            website=yc.get("website"),
                            city=loc["city"],
                            country=loc["country"],
                            country_code=loc["country_code"],
                            region=loc["region"],
                            latitude=loc["latitude"],
                            longitude=loc["longitude"],
                            ats_type=self.ats_type,
                            ats_slug=slug,
                            is_active=True,
                        )
                    )

                page += 1
                if page <= total_pages:
                    await asyncio.sleep(_DISCOVER_PAGE_DELAY)

        return stubs
