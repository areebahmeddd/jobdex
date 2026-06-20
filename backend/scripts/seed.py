"""Seed the JobDex database with well-known startup job boards.

Usage:
  python scripts/seed.py
"""

import asyncio

from app.database import get_session
from app.ingestion import INGESTERS

PASS = "\033[92m\u2713\033[0m"
FAIL = "\033[91m\u2717\033[0m"
WARN = "\033[93m!\033[0m"

# (ats_type, slug, display_name)
# ATS slugs verified against live boards. Update if a company changes provider.
COMPANIES: list[tuple[str, str, str]] = [
    # Greenhouse
    ("greenhouse", "airbnb", "Airbnb"),
    ("greenhouse", "shopify", "Shopify"),
    ("greenhouse", "doordash", "DoorDash"),
    ("greenhouse", "revolut", "Revolut"),
    ("greenhouse", "figma", "Figma"),
    ("greenhouse", "coinbase", "Coinbase"),
    ("greenhouse", "brex", "Brex"),
    ("greenhouse", "ramp", "Ramp"),
    ("greenhouse", "plaid", "Plaid"),
    ("greenhouse", "rippling", "Rippling"),
    ("greenhouse", "retool", "Retool"),
    # Ashby
    ("ashby", "linear", "Linear"),
    ("ashby", "notion", "Notion"),
    ("ashby", "vercel", "Vercel"),
    ("ashby", "loom", "Loom"),
    ("ashby", "mercury", "Mercury"),
    ("ashby", "anduril", "Anduril"),
    # Lever
    ("lever", "netflix", "Netflix"),
    ("lever", "spotify", "Spotify"),
]


async def main() -> None:
    """Ingest all configured startup job boards directly via the ingestion layer."""
    ok_count = 0
    warn_count = 0
    fail_count = 0

    print("\nJobDex Seed Script")
    print(f"{'=' * 60}\n")

    for ats, slug, name in COMPANIES:
        ingester = INGESTERS.get(ats)
        if not ingester:
            print(f"  {WARN} {name:<22} unknown ATS '{ats}'")
            warn_count += 1
            continue

        try:
            with get_session() as db:
                result = await ingester.ingest(slug, db)

            if result.total_fetched > 0:
                print(
                    f"  {PASS} {name:<22} [{ats}]  "
                    f"fetched={result.total_fetched} new={result.new_jobs} updated={result.updated_jobs}"
                )
                ok_count += 1
            else:
                print(f"  {WARN} {name:<22} [{ats}]  0 jobs (private or empty board)")
                warn_count += 1
        except Exception as exc:
            print(f"  {FAIL} {name:<22} [{ats}]  {exc}")
            fail_count += 1

    print(f"\n{'=' * 60}")
    print(f"  Done: {ok_count} ingested  {warn_count} empty/private  {fail_count} failed")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    asyncio.run(main())
