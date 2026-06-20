"""Enrich one company or all pending companies with Wikidata/Wikipedia data.

Usage:
  python scripts/enrich.py <slug>     # single company
  python scripts/enrich.py --all      # all companies with no enriched_at
"""

import asyncio
import sys

from app.config import settings
from app.database import get_session
from app.enrichment import enrich_company
from app.models import Company


async def enrich_one(slug: str) -> None:
    """Enrich a single company by slug."""
    with get_session() as db:
        result = await enrich_company(slug.lower(), db)
    print(f"Enriched {result.name} — updated: {result.updated_fields or 'nothing new'}")


async def enrich_all() -> None:
    """Enrich all active companies that have not yet been enriched."""
    with get_session() as db:
        slugs = [
            c.slug
            for c in db.query(Company)
            .filter(Company.is_active.is_(True), Company.enriched_at.is_(None))
            .order_by(Company.name)
            .all()
        ]

    if not slugs:
        print("No unenriched companies found.")
        return

    print(f"Enriching {len(slugs)} companies...")
    for slug in slugs:
        try:
            with get_session() as db:
                result = await enrich_company(slug, db)
            print(f"  {slug}: {result.updated_fields or 'nothing new'}")
        except Exception as exc:
            print(f"  {slug}: error — {exc}")
        await asyncio.sleep(settings.ENRICHMENT_STEP_DELAY)

    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/enrich.py <slug>  OR  python scripts/enrich.py --all")
        sys.exit(1)

    if sys.argv[1] == "--all":
        asyncio.run(enrich_all())
    else:
        asyncio.run(enrich_one(sys.argv[1]))
