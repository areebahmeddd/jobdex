"""Probe YC-discovered companies against Greenhouse, Ashby, and Lever.

For each YC company in the database, probes supported ATS providers in order.
The first match is ingested, giving the company full job listings instead of
the single YC representative job.

Run after scripts/discover.py.

Usage:
  python scripts/seed.py
"""

import asyncio

from app.config import settings
from app.database import get_session
from app.ingestion import INGESTERS
from app.models import Company

PASS = "\033[92m\u2713\033[0m"
FAIL = "\033[91m\u2717\033[0m"

PROBE_ORDER = ["ashby", "greenhouse", "lever"]


async def main() -> None:
    """Probe all YC companies against each ATS in PROBE_ORDER."""
    with get_session() as db:
        slugs = [
            c.slug
            for c in db.query(Company)
            .filter(Company.ats_type == "ycombinator", Company.is_active.is_(True))
            .order_by(Company.name)
            .all()
        ]

    if not slugs:
        print("No YCombinator companies in DB. Run scripts/discover.py first.")
        return

    print(f"\nJobDex Seed \u2014 probing {len(slugs)} YC companies across {PROBE_ORDER}")
    print(f"{'=' * 50}\n")

    matched = 0
    errors = 0

    for i, slug in enumerate(slugs, 1):
        found = False

        for ats_name in PROBE_ORDER:
            ingester = INGESTERS[ats_name]
            try:
                if not await ingester.probe(slug):
                    await asyncio.sleep(settings.CRAWL_DELAY)
                    continue

                with get_session() as db:
                    result = await ingester.ingest(slug, db)

                print(
                    f"  {PASS} {slug:<30} [{ats_name:<10}]  "
                    f"fetched={result.total_fetched}  new={result.new_jobs}"
                )
                matched += 1
                found = True
                break

            except Exception as exc:
                print(f"  {FAIL} {slug:<30} [{ats_name}]  {exc}")
                errors += 1
                await asyncio.sleep(settings.CRAWL_DELAY)

        if not found and i % 100 == 0:
            print(f"  ... {i}/{len(slugs)} probed \u2014 {matched} upgraded so far")

    print(f"\n{'=' * 50}")
    print(
        f"  Done: {matched} upgraded to richer ATS  {len(slugs) - matched} remain YC-only  {errors} errors"
    )
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    asyncio.run(main())
