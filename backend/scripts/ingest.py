"""One-shot ingestion for a single company board.

Usage:
  python scripts/ingest.py <ats> <slug>
  python scripts/ingest.py greenhouse airbnb
  python scripts/ingest.py lever netflix
  python scripts/ingest.py ashby linear
"""

import asyncio
import sys

from app.database import get_session
from app.ingestion import INGESTERS


async def main(ats: str, slug: str) -> None:
    """Ingest jobs for the given ATS type and company slug."""
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


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/ingest.py <ats> <slug>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1].lower(), sys.argv[2].lower()))
