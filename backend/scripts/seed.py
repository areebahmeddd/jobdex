"""Seed the JobDex database with well-known startup job boards.

Usage:
  python scripts/seed.py [--base-url http://127.0.0.1:8000] [--api-key KEY]

Pass --api-key if ADMIN_API_KEY is set in .env.
"""

import argparse
import time

import httpx

BASE = "http://127.0.0.1:8000"
HEADERS: dict[str, str] = {}

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

ok_count = 0
fail_count = 0
warn_count = 0


def ingest(ats: str, slug: str, name: str) -> None:
    global ok_count, fail_count, warn_count
    try:
        r = httpx.post(f"{BASE}/ingest/{ats}/{slug}", headers=HEADERS, timeout=90.0)
        if r.status_code == 200:
            d = r.json()
            fetched = d.get("total_fetched", 0)
            new = d.get("new_jobs", 0)
            updated = d.get("updated_jobs", 0)
            if fetched > 0:
                print(f"  {PASS} {name:<22} [{ats}]  fetched={fetched} new={new} updated={updated}")
                ok_count += 1
            else:
                print(f"  {WARN} {name:<22} [{ats}]  0 jobs (private or empty board)")
                warn_count += 1
        elif r.status_code == 403:
            print(f"  {FAIL} {name:<22}  403 Forbidden — pass --api-key")
            fail_count += 1
        else:
            print(f"  {FAIL} {name:<22}  HTTP {r.status_code}: {r.text[:100]}")
            fail_count += 1
    except httpx.TimeoutException:
        print(f"  {FAIL} {name:<22}  Timed out")
        fail_count += 1
    except Exception as exc:
        print(f"  {FAIL} {name:<22}  {exc}")
        fail_count += 1
    time.sleep(0.4)


def main() -> None:
    global BASE, HEADERS
    parser = argparse.ArgumentParser(description="Seed JobDex with known startup job boards")
    parser.add_argument("--base-url", default=BASE)
    parser.add_argument("--api-key", default="", help="X-API-Key header value")
    args = parser.parse_args()

    BASE = args.base_url.rstrip("/")
    if args.api_key:
        HEADERS["X-API-Key"] = args.api_key

    print("\nJobDex Seed Script")
    print(f"Target: {BASE}")
    print(f"{'=' * 60}\n")

    for ats, slug, name in COMPANIES:
        ingest(ats, slug, name)

    print(f"\n{'=' * 60}")
    print(f"  Done: {ok_count} ingested  {warn_count} empty/private  {fail_count} failed")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
