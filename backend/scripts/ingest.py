"""Ingest job listings for all active companies or a single company board.

Usage:
  python scripts/ingest.py --all                        # all active companies
  python scripts/ingest.py <ats> <slug>                 # single company
  python scripts/ingest.py greenhouse airbnb
  python scripts/ingest.py lever netflix
  python scripts/ingest.py ashby linear

Flags:
  --force   Bypass the server-live check; concurrent runs risk dedup conflicts.
"""

import asyncio
import sys
import urllib.request

from app.config import settings
from app.database import get_session
from app.ingestion import INGESTERS
from app.scheduler import run_ingestion


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


async def main() -> None:
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--force"]

    _abort_if_server_live(force=force)

    if len(args) == 1 and args[0] == "--all":
        await run_ingestion()
        return

    if len(args) == 2:
        ats, slug = args[0].lower(), args[1].lower()
        ingester = INGESTERS.get(ats)
        if not ingester:
            print(f"Unknown ATS '{ats}'. Valid options: {list(INGESTERS)}")
            sys.exit(1)

        print(f"Ingesting {slug} from {ats}...")
        with get_session() as db:
            result = await ingester.ingest(slug, db)
        print(
            f"Done: fetched={result.total_fetched} new={result.new_jobs} "
            f"updated={result.updated_jobs} deactivated={result.deactivated_jobs}"
        )
        if result.errors:
            print(f"Errors: {result.errors}")
        return

    print(
        "Usage: python scripts/ingest.py --all  "
        "OR  python scripts/ingest.py <ats> <slug>  "
        "[--force]"
    )
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
