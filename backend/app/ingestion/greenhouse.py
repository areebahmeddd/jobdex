"""Greenhouse ATS ingester.

Public API, no auth required.
Endpoint: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.config import settings
from app.ingestion.base import BaseIngester
from app.ingestion.normalizer import (
    classify_role,
    classify_seniority,
    extract_tech_stack,
    make_snippet,
    normalize_location,
    strip_html,
)
from app.models import Company, Job

_BASE = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseIngester(BaseIngester):
    ats_type = "greenhouse"

    async def fetch_raw(self, slug: str) -> list[dict]:
        url = f"{_BASE}/{slug}/jobs?content=true"
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json().get("jobs", [])

    def get_job_id(self, raw: dict) -> str:
        return str(raw["id"])

    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        title = raw.get("title", "")

        loc_raw = (raw.get("location") or {}).get("name", "")
        if not loc_raw:
            offices = raw.get("offices") or []
            if offices:
                loc_raw = offices[0].get("name", "")

        departments = raw.get("departments") or []
        department = departments[0].get("name", "") if departments else ""

        html = raw.get("content", "") or ""
        plain = strip_html(html)

        loc = normalize_location(
            loc_raw,
            fallback_city=company.city,
            fallback_country_code=company.country_code,
        )
        category, subcategory = classify_role(title, plain, department)
        seniority = classify_seniority(title)
        tech = extract_tech_stack(title, plain[:2000])
        posted_at = _parse_dt(raw.get("updated_at", ""))

        return Job(
            company_id=company.id,
            title=title,
            title_normalized=title.lower().strip(),
            description=plain[:20000],
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
            department=department,
            source_url=raw.get("absolute_url", ""),
            ats_type=self.ats_type,
            ats_job_id=str(raw["id"]),
            posted_at=posted_at,
            is_active=True,
        )


def _parse_dt(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
