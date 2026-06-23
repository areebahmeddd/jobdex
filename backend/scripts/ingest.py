"""Ingest job listings for all active companies or a single company board.

Usage:
  python scripts/ingest.py --all                  # all active companies
  python scripts/ingest.py <ats> <slug>           # single company
  python scripts/ingest.py greenhouse airbnb
  python scripts/ingest.py lever netflix
  python scripts/ingest.py ashby linear
"""

import asyncio
import sys

from app.database import get_session
from app.ingestion import INGESTERS
from app.scheduler import run_ingestion


async def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--all":
        await run_ingestion()
        return

    if len(sys.argv) == 3:
        ats, slug = sys.argv[1].lower(), sys.argv[2].lower()
        ingester = INGESTERS.get(ats)
        if not ingester:
            print(f"Unknown ATS '{ats}'. Valid options: {list(INGESTERS)}")
            sys.exit(1)

        print(f"Ingesting {slug} from {ats}...")
        with get_session() as db:
            result = await ingester.ingest(slug, db)
        print(
            f"Done — fetched={result.total_fetched} new={result.new_jobs} "
            f"updated={result.updated_jobs} deactivated={result.deactivated_jobs}"
        )
        if result.errors:
            print(f"Errors: {result.errors}")
        return

    print("Usage: python scripts/ingest.py --all  OR  python scripts/ingest.py <ats> <slug>")
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
