from __future__ import annotations

import asyncio
import hashlib
from abc import ABC, abstractmethod
from datetime import UTC, datetime

import httpx
from loguru import logger
from sqlalchemy.orm import Session

from app.ingestion.normalizer import get_region_for_country, is_blocked_location
from app.models import Company, Job
from app.schemas import IngestResponse

# Shared limits used by all ingester build_job() implementations.
_TECH_EXTRACT_CHARS: int = 2000  # description chars passed to extract_tech_stack
_DESCRIPTION_MAX_CHARS: int = 20000  # max chars stored in job.description


def _backfill_company_hq(company: Company, db: Session) -> None:
    """Set company HQ fields from the most common city across its active jobs."""
    from sqlalchemy import func

    top_city = (
        db.query(Job.city)
        .filter(Job.company_id == company.id, Job.city.isnot(None), Job.is_active.is_(True))
        .group_by(Job.city)
        .order_by(func.count().desc())
        .limit(1)
        .scalar()
    )
    if not top_city:
        return
    row = (
        db.query(Job)
        .filter(Job.company_id == company.id, Job.city == top_city, Job.is_active.is_(True))
        .first()
    )
    if row:
        company.city = row.city
        company.country = row.country
        company.country_code = row.country_code
        company.region = row.region
        company.latitude = row.latitude
        company.longitude = row.longitude


async def _fetch_company_geo(name: str) -> dict:
    """Query Clearbit autocomplete for company HQ city, country, coordinates, and logo URL."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                "https://autocomplete.clearbit.com/v1/companies/suggest",
                params={"query": name},
            )
            if r.status_code != 200:
                return {}
            results = r.json()
            if not results:
                return {}
            top = results[0]
            geo = top.get("geo") or {}
            return {
                "city": geo.get("city"),
                "country_code": geo.get("countryCode"),
                "country": geo.get("country"),
                "latitude": geo.get("lat"),
                "longitude": geo.get("lng"),
                "logo_url": (
                    f"https://logo.clearbit.com/{top['domain']}" if top.get("domain") else None
                ),
            }
    except Exception:
        return {}


class BaseIngester(ABC):
    ats_type: str  # must be set by subclass

    @abstractmethod
    async def fetch_raw(self, slug: str) -> list[dict]:
        """Call the ATS API and return raw job dicts."""
        ...

    @abstractmethod
    def extract_job_id(self, raw: dict) -> str:
        """Extract the stable job ID from a raw job dict."""
        ...

    @abstractmethod
    def build_job(self, raw: dict, company: Company, slug: str) -> Job:
        """Parse a raw job dict into an unsaved Job ORM object."""
        ...

    def make_hash(self, slug: str, job_id: str) -> str:
        """Compute a SHA-256 dedup hash from the ATS type, slug, and job ID."""
        return hashlib.sha256(f"{self.ats_type}:{slug}:{job_id}".encode()).hexdigest()

    def _resolve_company(self, slug: str, db: Session) -> Company:
        """Return the Company for this slug, creating a stub if needed."""
        company = (
            db.query(Company)
            .filter(Company.ats_slug == slug, Company.ats_type == self.ats_type)
            .first()
        )
        if company is None:
            company = db.query(Company).filter(Company.slug == slug).first()
        if company is None:
            logger.info(f"[{self.ats_type}] '{slug}' creating company stub")
            company = Company(
                name=slug.replace("-", " ").title(),
                slug=slug,
                ats_type=self.ats_type,
                ats_slug=slug,
            )
            db.add(company)
            db.flush()
        return company

    async def ingest(self, slug: str, db: Session) -> IngestResponse:
        """Fetch jobs from the ATS, upsert new and updated records, and deactivate expired ones."""
        result = IngestResponse(company_slug=slug, ats_type=self.ats_type)
        company = self._resolve_company(slug, db)

        if not company.latitude:
            geo = await _fetch_company_geo(company.name)
            if geo and not is_blocked_location(geo.get("country_code"), geo.get("city")):
                if geo.get("latitude") and geo.get("longitude"):
                    company.latitude = geo["latitude"]
                    company.longitude = geo["longitude"]
                if geo.get("city") and not company.city:
                    company.city = geo["city"]
                if geo.get("country_code") and not company.country_code:
                    company.country_code = geo["country_code"]
                    company.region = get_region_for_country(geo["country_code"])
                if geo.get("country") and not company.country:
                    company.country = geo["country"]
                if geo.get("logo_url") and not company.logo_url:
                    company.logo_url = geo["logo_url"]
                logger.debug(
                    f"[{self.ats_type}] '{slug}' geocoded HQ: {company.city}, {company.country_code}"
                )

        try:
            raw_jobs = await self.fetch_raw(slug)
        except httpx.HTTPStatusError as exc:
            msg = f"HTTP {exc.response.status_code} from {self.ats_type} board '{slug}'"
            logger.error(msg)
            result.errors.append(msg)
            company.crawl_error = msg
            db.commit()
            return result
        except httpx.RequestError as exc:
            msg = f"Network error from {self.ats_type} board '{slug}': {exc}"
            logger.error(msg)
            result.errors.append(msg)
            company.crawl_error = msg
            db.commit()
            return result

        result.total_fetched = len(raw_jobs)
        logger.info(f"[{self.ats_type}] '{slug}' -> {len(raw_jobs)} raw jobs")

        # All dedup hashes for this company.
        existing_rows = (
            db.query(Job.dedup_hash, Job.id, Job.is_active)
            .filter(Job.company_id == company.id, Job.dedup_hash.isnot(None))
            .all()
        )
        existing_hash_to_id: dict[str, str] = {r.dedup_hash: r.id for r in existing_rows}
        active_hashes: set[str] = {r.dedup_hash for r in existing_rows if r.is_active}
        seen_hashes: set[str] = set()

        now = datetime.now(tz=UTC)

        for raw in raw_jobs:
            try:
                job_id = self.extract_job_id(raw)
                dedup_hash = self.make_hash(slug, job_id)
                seen_hashes.add(dedup_hash)
                if dedup_hash in existing_hash_to_id:
                    db.query(Job).filter(Job.id == existing_hash_to_id[dedup_hash]).update(
                        {"last_seen_at": now, "is_active": True},
                        synchronize_session=False,
                    )
                    result.updated_jobs += 1
                else:
                    job = self.build_job(raw, company, slug)
                    if is_blocked_location(job.country_code, job.city):
                        logger.info(
                            f"[{self.ats_type}] '{slug}' skipping blocked location:"
                            f" {job.city}, {job.country_code}"
                        )
                        seen_hashes.discard(dedup_hash)
                        continue
                    job.dedup_hash = dedup_hash
                    job.first_seen_at = now
                    job.last_seen_at = now
                    db.add(job)
                    result.new_jobs += 1
            except Exception as exc:  # noqa: BLE001
                msg = f"Error on job id={raw.get('id', '?')}: {exc}"
                logger.warning(msg)
                result.errors.append(msg)

            await asyncio.sleep(0)

        expired = active_hashes - seen_hashes
        if expired:
            db.query(Job).filter(Job.dedup_hash.in_(expired)).update(
                {"is_active": False}, synchronize_session=False
            )
            result.deactivated_jobs = len(expired)
            logger.info(f"[{self.ats_type}] '{slug}' deactivated {len(expired)} expired jobs")

        company.last_crawled_at = now
        company.ats_type = self.ats_type
        company.ats_slug = slug
        company.crawl_error = None

        # Backfill company HQ if it was a stub.
        if company.city is None:
            _backfill_company_hq(company, db)

        db.commit()

        logger.info(
            f"[{self.ats_type}] '{slug}' done - "
            f"new={result.new_jobs} updated={result.updated_jobs} "
            f"deactivated={result.deactivated_jobs} errors={len(result.errors)}"
        )
        return result

    async def probe(self, slug: str) -> bool:
        """Return True if this ATS has a valid board for the given slug."""
        try:
            jobs = await self.fetch_raw(slug)
            return isinstance(jobs, list)
        except Exception:
            return False
