import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.config import settings
from app.database import get_session
from app.enrichment import enrich_company
from app.ingestion import INGESTERS
from app.models import Company

scheduler = AsyncIOScheduler(timezone="UTC")


async def run_ingestion() -> None:
    """Crawl all active companies and ingest their latest job listings."""
    logger.info("[scheduler] ingestion run started")
    total_new = 0
    total_updated = 0
    errors = 0

    with get_session() as db:
        targets = [
            (company.ats_type, company.ats_slug, company.slug)
            for company in db.query(Company)
            .filter(Company.is_active.is_(True), Company.ats_type.isnot(None))
            .order_by(Company.last_crawled_at.asc().nullsfirst())
            .all()
        ]

    for ats_type, ats_slug, slug in targets:
        ingester = INGESTERS.get(ats_type)
        if not ingester:
            continue
        try:
            with get_session() as db:
                result = await ingester.ingest(ats_slug, db)
            total_new += result.new_jobs
            total_updated += result.updated_jobs
        except Exception as exc:
            logger.warning(f"[scheduler] ingest failed for {slug}: {exc}")
            errors += 1
        await asyncio.sleep(settings.CRAWL_DELAY)

    logger.info(
        f"[scheduler] ingestion complete — new={total_new} updated={total_updated} errors={errors}"
    )


async def run_enrichment() -> None:
    """Enrich companies that have not yet been enriched with Wikidata/Wikipedia data."""
    logger.info("[scheduler] enrichment run started")
    enriched = 0
    errors = 0

    with get_session() as db:
        slugs = [
            company.slug
            for company in db.query(Company)
            .filter(Company.is_active.is_(True), Company.enriched_at.is_(None))
            .order_by(Company.name)
            .all()
        ]

    for slug in slugs:
        try:
            with get_session() as db:
                await enrich_company(slug, db)
            enriched += 1
        except Exception as exc:
            logger.warning(f"[scheduler] enrichment failed for {slug}: {exc}")
            errors += 1
        await asyncio.sleep(settings.ENRICHMENT_STEP_DELAY)

    logger.info(f"[scheduler] enrichment complete — enriched={enriched} errors={errors}")


async def run_discovery() -> None:
    """Register new companies from ingesters that support bulk discovery."""
    logger.info("[scheduler] discovery run started")
    added = 0
    skipped = 0

    for ats_name, ingester in INGESTERS.items():
        try:
            stubs = await ingester.discover()
        except Exception as exc:
            logger.error(f"[scheduler] discovery failed for {ats_name}: {exc}")
            continue

        if not stubs:
            continue

        stub_slugs = [s.slug for s in stubs]
        with get_session() as db:
            existing_slugs = {
                row.slug
                for row in db.query(Company.slug).filter(Company.slug.in_(stub_slugs)).all()
            }
            new_stubs = [s for s in stubs if s.slug not in existing_slugs]
            for stub in new_stubs:
                db.add(stub)
            db.commit()
        added += len(new_stubs)
        skipped += len(stubs) - len(new_stubs)

    logger.info(f"[scheduler] discovery complete — added={added} skipped={skipped}")


def start() -> None:
    """Register scheduled jobs and start the background scheduler."""
    scheduler.add_job(
        run_ingestion,
        "interval",
        hours=settings.INGEST_INTERVAL_HOURS,
        id="ingest_all",
        max_instances=1,
    )
    scheduler.add_job(
        run_enrichment,
        "interval",
        hours=settings.ENRICH_INTERVAL_HOURS,
        id="enrich_pending",
        max_instances=1,
    )
    scheduler.add_job(
        run_discovery,
        "interval",
        hours=settings.DISCOVER_INTERVAL_HOURS,
        id="discover_companies",
        max_instances=1,
    )
    scheduler.start()
    logger.info(
        f"[scheduler] started — ingest every {settings.INGEST_INTERVAL_HOURS}h, "
        f"enrich every {settings.ENRICH_INTERVAL_HOURS}h, "
        f"discover every {settings.DISCOVER_INTERVAL_HOURS}h"
    )


def stop() -> None:
    """Shut down the scheduler cleanly."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[scheduler] stopped")
