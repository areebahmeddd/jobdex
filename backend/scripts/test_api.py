"""Test every endpoint and write full responses to test_api_output.json.

Usage:
  python scripts/test_api.py [--base-url http://127.0.0.1:8000]
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

OUTPUT = Path(__file__).parent / "test_api_output.json"


def get(client: httpx.Client, url: str, **params) -> dict:
    r = client.get(url, params=params)
    return {"status": r.status_code, "body": r.json()}


def post(client: httpx.Client, url: str, headers: dict) -> dict:
    r = client.post(url, headers=headers)
    return {"status": r.status_code, "body": r.json()}


def run(base: str) -> dict:
    results: dict = {
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": base,
    }

    with httpx.Client(base_url=base, timeout=60.0) as c:
        print("  GET /health")
        results["health"] = get(c, "/health")

        print("  GET /stats")
        results["stats"] = get(c, "/stats")

        print("  GET /companies")
        comp_list = get(c, "/companies", limit=50)
        results["companies_list"] = comp_list

        slugs = [co["slug"] for co in comp_list["body"].get("companies", [])]
        print(f"    Found slugs: {slugs}")

        # Detail + jobs for every seeded company
        results["company_details"] = {}
        results["company_jobs"] = {}

        for slug in slugs:
            print(f"  GET /companies/{slug}")
            results["company_details"][slug] = get(c, f"/companies/{slug}")

            print(f"  GET /companies/{slug}/jobs")
            results["company_jobs"][slug] = get(c, f"/companies/{slug}/jobs", limit=5)

        print("  GET /jobs")
        jobs_list = get(c, "/jobs", limit=5)
        results["jobs_list"] = jobs_list

        first_job_id = (jobs_list["body"].get("jobs") or [{}])[0].get("id")
        if first_job_id:
            print(f"  GET /jobs/{first_job_id}")
            results["job_detail"] = get(c, f"/jobs/{first_job_id}")

        for query in ["engineering", "design", "remote"]:
            print(f"  GET /search?q={query}")
            results[f"search_{query}"] = get(c, "/search", q=query, limit=3)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    print("\nJobDex API Test")
    print(f"Target : {args.base_url}")
    print(f"Output : {OUTPUT}")
    print("=" * 50)

    try:
        data = run(args.base_url)
    except httpx.ConnectError:
        print("\nERROR: could not connect. Is the backend running?")
        sys.exit(1)

    OUTPUT.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"\nDone. Results saved to {OUTPUT}")


if __name__ == "__main__":
    main()
