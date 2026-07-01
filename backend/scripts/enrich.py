"""Enrich one company or all pending companies with Wikidata/Wikipedia data.

Usage:
  python scripts/enrich.py <slug>           # single company
  python scripts/enrich.py --all            # all companies with no enriched_at

Flags:
  --force   Skip the server-live check and run even if the API is up.
"""

import asyncio
import sys
import urllib.request

from app.config import settings
from app.database import get_session
from app.enrichment import enrich_company
from app.models import Company


def _abort_if_server_live(*, force: bool) -> None:
    """Exit with a warning when the API server is reachable and --force was not passed."""
    if force:
        return
    try:
        with urllib.request.urlopen(f"{settings.API_URL}/health", timeout=2) as r:
            if r.status == 200:
                print(
                    "\u26a0  A JobDex server is running. Concurrent scripts risk noisy dedup "
                    "errors and double ATS traffic.\n"
                    "   Stop the server first, or pass --force to proceed anyway."
                )
                sys.exit(1)
    except Exception:
        pass  # server not reachable; safe to proceed


async def enrich_one(slug: str) -> None:
    """Enrich a single company by slug."""
    with get_session() as db:
        result = await enrich_company(slug.lower(), db)
    print(f"Enriched {result.name}: {result.updated_fields or 'nothing new'}")


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
            print(f"  {slug}: {exc}")
        await asyncio.sleep(settings.ENRICHMENT_STEP_DELAY)

    print("Done.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--force"]

    if len(args) != 1:
        print(
            "Usage: python scripts/enrich.py <slug>  OR  python scripts/enrich.py --all  [--force]"
        )
        sys.exit(1)

    _abort_if_server_live(force=force)

    if args[0] == "--all":
        asyncio.run(enrich_all())
    else:
        asyncio.run(enrich_one(args[0]))
