"""Auto-detect the ATS provider for a company and ingest from the first match.

Usage:
  python scripts/discover.py <slug>
  python scripts/discover.py notion
"""

import asyncio
import sys

from app.config import settings
from app.database import get_session
from app.ingestion import INGESTERS


async def main(slug: str) -> None:
    """Probe all supported ATS providers and ingest from the first that responds."""
    slug = slug.lower()
    print(f"Probing ATS providers for '{slug}'...")

    for ats_name, ingester in INGESTERS.items():
        print(f"  Trying {ats_name}...", end=" ", flush=True)
        try:
            found = await ingester.probe(slug)
        except Exception as exc:
            print(f"error ({exc})")
            found = False

        if found:
            print("found")
            with get_session() as db:
                result = await ingester.ingest(slug, db)
            print(
                f"Ingested from {ats_name} — fetched={result.total_fetched} "
                f"new={result.new_jobs} updated={result.updated_jobs}"
            )
            return

        print("not found")
        await asyncio.sleep(settings.CRAWL_DELAY)

    print(f"Not found on any ATS provider: {list(INGESTERS)}")
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/discover.py <slug>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
