import asyncio
from datetime import UTC, datetime

import httpx2 as httpx
from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.enrichment import wikidata, wikipedia
from app.models import Company
from app.schemas import EnrichResponse


async def enrich_company(slug: str, db: Session) -> EnrichResponse:
    """Enrich a company record using Wikidata and Wikipedia; return a summary of changes."""
    company = db.query(Company).filter(Company.slug == slug).first()
    if not company:
        raise ValueError(f"Company '{slug}' not found")

    logger.info(f"[enrichment] Starting enrichment for: {company.name}")
    updated_fields: list[str] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": settings.ENRICHMENT_BOT_AGENT},
        follow_redirects=True,
    ) as client:
        qid = company.wikidata_id
        if not qid:
            qid = await wikidata.search_company(client, company.name)
            await asyncio.sleep(settings.ENRICHMENT_STEP_DELAY)

        wikidata_data: dict = {}
        if qid:
            wikidata_data = await wikidata.fetch_company_data(client, qid)
            await asyncio.sleep(settings.ENRICHMENT_STEP_DELAY)

            if wikidata_data:
                company.wikidata_id = qid

                social = {
                    "twitter": f"https://twitter.com/{wikidata_data['twitter']}"
                    if wikidata_data.get("twitter")
                    else None,
                    "instagram": f"https://instagram.com/{wikidata_data['instagram']}"
                    if wikidata_data.get("instagram")
                    else None,
                    "linkedin": f"https://linkedin.com/company/{wikidata_data['linkedin']}"
                    if wikidata_data.get("linkedin")
                    else None,
                    "facebook": f"https://facebook.com/{wikidata_data['facebook']}"
                    if wikidata_data.get("facebook")
                    else None,
                    "github": f"https://github.com/{wikidata_data['github']}"
                    if wikidata_data.get("github")
                    else None,
                    "website": wikidata_data.get("website"),
                }
                existing_social = company.social_links or {}
                merged_social = {k: v for k, v in {**existing_social, **social}.items() if v}
                if merged_social:
                    company.social_links = merged_social
                    updated_fields.append("social_links")

                if not company.website and wikidata_data.get("website"):
                    company.website = wikidata_data["website"]
                    updated_fields.append("website")

                if not company.founded_year and wikidata_data.get("founded_year"):
                    company.founded_year = wikidata_data["founded_year"]
                    updated_fields.append("founded_year")

                if not company.city and wikidata_data.get("hq"):
                    company.city = wikidata_data["hq"]
                    updated_fields.append("city")

                if wikidata_data.get("industries"):
                    existing_industry = company.industry or []
                    merged = list({*existing_industry, *wikidata_data["industries"]})
                    company.industry = merged
                    updated_fields.append("industry")

                if wikidata_data.get("founders"):
                    company.founders = wikidata_data["founders"]
                    updated_fields.append("founders")

                if not company.headcount_range and wikidata_data.get("employee_count"):
                    try:
                        n = int(float(wikidata_data["employee_count"]))
                        company.headcount_range = _bucket_headcount(n)
                        updated_fields.append("headcount_range")
                    except (ValueError, TypeError):
                        pass
        else:
            logger.info(f"[enrichment] No Wikidata entity found for '{company.name}'")

        if not company.description:
            about = await wikipedia.find_summary(
                client, company.name, wikidata_qid=company.wikidata_id
            )
            await asyncio.sleep(settings.ENRICHMENT_STEP_DELAY)
            if about:
                company.description = about
                updated_fields.append("description")

    company.enriched_at = datetime.now(UTC)
    db.commit()
    db.refresh(company)

    logger.info(
        f"[enrichment] Done for '{company.name}': "
        f"updated {len(updated_fields)} fields: {updated_fields}"
    )
    return EnrichResponse(
        slug=slug,
        name=company.name,
        wikidata_id=company.wikidata_id,
        updated_fields=updated_fields,
        enriched_at=company.enriched_at,
    )


def _bucket_headcount(n: int) -> str:
    """Map a raw employee count to a standard headcount range band."""
    if n <= 10:
        return "1-10"
    if n <= 50:
        return "11-50"
    if n <= 200:
        return "51-200"
    if n <= 500:
        return "201-500"
    if n <= 1000:
        return "501-1000"
    return "1000+"
