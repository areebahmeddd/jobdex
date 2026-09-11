"""Probe YC-discovered companies against the slug-addressed ATS.

For each YC company in the database, probes supported ATS providers in order.
The first match is ingested, giving the company full job listings instead of
the single YC representative job.

Run after scripts/discover.py.

Usage:
  python scripts/probe.py
  python scripts/probe.py --force   # bypass server-live check

Flags:
  --force   Bypass the server-live check; concurrent runs risk dedup conflicts.
"""

import asyncio
import sys
import urllib.request

from app.config import settings
from app.database import get_session
from app.ingestion import INGESTERS
from app.models import Company

PASS = "\033[92m\u2713\033[0m"
FAIL = "\033[91m\u2717\033[0m"

# First match wins. MCF is absent because it addresses companies by UEN, not by slug.
PROBE_ORDER = [
    "ashby",
    "greenhouse",
    "lever",
    "smartrecruiters",
    "workable",
    "recruitee",
    "pyjamahr",
]


def _abort_if_server_live(*, force: bool) -> None:
    """Exit with a warning when the API server is reachable and --force was not passed."""
    if force:
        return
    try:
        with urllib.request.urlopen(f"{settings.API_URL}/health", timeout=2) as r:
            if r.status == 200:
                print(
                    "⚠  A JobDex server is running. Concurrent scripts risk noisy dedup "
                    "errors and double ATS traffic.\n"
                    "   Stop the server first, or pass --force to proceed anyway."
                )
                sys.exit(1)
    except Exception:
        pass  # server not reachable; safe to proceed


async def main() -> None:
    """Probe all YC companies against each ATS in PROBE_ORDER."""
    _abort_if_server_live(force="--force" in sys.argv)

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

    print(f"\nJobDex Seed - probing {len(slugs)} YC companies across {PROBE_ORDER}")
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
            print(f"  ... {i}/{len(slugs)} probed, {matched} upgraded so far")

    print(f"\n{'=' * 50}")
    print(
        f"  Done: {matched} upgraded to richer ATS  {len(slugs) - matched} remain YC-only  {errors} errors"
    )
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    asyncio.run(main())
