"""Integration tests for the running JobDex server.

Usage:
  python scripts/validate.py [--base-url http://127.0.0.1:8000]

Tests:
  1.  Health check
  2.  Root endpoint structure
  3.  Cities endpoint (all, featured, India, Middle East)
  4.  GET /jobs basic
  5.  City alias canonicalization (Bengaluru -> Bangalore, NYC -> New York)
  6.  GET /search - primary map endpoint
  7.  GET /search region=south_asia
  8.  GET /search region=middle_east
  9.  GET /search role=engineering
  10. GET /companies + /companies/{slug}
  11. GET /stats
  12. Data quality - lat/lng, source_url, role_category coverage
"""

import argparse
import sys
from typing import Any

import httpx

BASE = "http://127.0.0.1:8000"

PASS = "\033[92m\u2713\033[0m"
FAIL = "\033[91m\u2717\033[0m"
WARN = "\033[93m!\033[0m"

errors: list[str] = []
warnings: list[str] = []


def ok(label: str, detail: str = ""):
    """Print a passing result line to the console."""
    suffix = f"  {detail}" if detail else ""
    print(f"  {PASS} {label}{suffix}")


def fail(label: str, detail: str = ""):
    """Print a failing result line and record the error."""
    suffix = f"  {detail}" if detail else ""
    print(f"  {FAIL} {label}{suffix}")
    errors.append(f"{label}: {detail}")


def warn(label: str, detail: str = ""):
    """Print a warning result line and record the warning."""
    suffix = f"  {detail}" if detail else ""
    print(f"  {WARN} {label}{suffix}")
    warnings.append(f"{label}: {detail}")


def get(
    path: str, params: dict | None = None, timeout: float = 15, headers: dict | None = None
) -> httpx.Response:
    """Send a GET request to the local API and return the response."""
    return httpx.get(f"{BASE}{path}", params=params, timeout=timeout, headers=headers or {})


def section(title: str):
    """Print a formatted section header to the console."""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# Tests


def test_health():
    """Verify the health endpoint returns status ok."""
    section("1. Health check")
    r = get("/health")
    if r.status_code == 200 and r.json().get("status") == "ok":
        ok("GET /health", f"version={r.json().get('version')}")
    else:
        fail("GET /health", f"status={r.status_code}")


def test_root():
    """Verify the root endpoint returns expected metadata keys."""
    section("2. Root endpoint")
    r = get("/")
    d = r.json()
    if "endpoints" in d and "supported_ats" in d:
        ok("GET /", f"ATS={d['supported_ats']}")
    else:
        fail("GET /", "missing keys")


def test_cities():
    """Verify city listing with global, featured, India, and Middle East filters."""
    section("3. Cities endpoint")

    r = get("/cities")
    d = r.json()
    total = d.get("total", 0)
    ok("GET /cities total", f"{total} cities")

    r = get("/cities", {"featured_only": "true"})
    featured = r.json()
    if len(featured) >= 5:
        ok("GET /cities?featured_only=true", f"{len(featured)} featured")
    else:
        warn("GET /cities?featured_only=true", f"only {len(featured)} featured")

    r = get("/cities", {"country_code": "IN"})
    india = r.json()
    if len(india) >= 5:
        ok("GET /cities?country_code=IN", f"{len(india)} Indian cities")
    else:
        warn("GET /cities?country_code=IN", f"only {len(india)} - expected >= 5")

    r = get("/cities", {"region": "middle_east"})
    me = r.json()
    if len(me) >= 5:
        ok("GET /cities?region=middle_east", f"{len(me)} ME cities")
    else:
        warn("GET /cities?region=middle_east", f"only {len(me)} - expected >= 5")


def test_jobs_list():
    """Verify the jobs listing endpoint returns results with required fields."""
    section("4. Jobs list")
    r = get("/jobs")
    d = r.json()
    total = d.get("total", 0)
    if total > 0:
        ok("GET /jobs", f"total={total}")
        j0 = d["jobs"][0]
        for field in (
            "id",
            "title",
            "company_name",
            "latitude",
            "longitude",
            "source_url",
        ):
            if j0.get(field) is None:
                warn(f"job[0].{field}", "is None")
    else:
        warn("GET /jobs", "0 jobs - ingest data first")


def test_city_alias():
    """Verify that city aliases resolve to the same job counts as canonical city names."""
    section("5. City alias canonicalization")

    def check(alias: str, canonical: str):
        r_alias = get("/jobs", {"city": alias})
        r_canon = get("/jobs", {"city": canonical})
        ta = r_alias.json()["total"]
        tc = r_canon.json()["total"]
        if ta == tc:
            ok(f"{alias!r} -> {canonical!r}", f"{ta} jobs")
        else:
            warn(f"{alias!r} vs {canonical!r}", f"{alias}={ta}  {canonical}={tc}")

    check("Bengaluru", "Bangalore")
    check("Bombay", "Mumbai")
    check("NCR", "Delhi")
    check("NYC", "New York")


def test_search():
    """Verify the search endpoint returns the expected envelope structure and fields."""
    section("6. Primary search endpoint")
    r = get("/search")
    d = r.json()
    if "jobs" in d and "companies" in d:
        ok("GET /search", f"jobs={d['total_jobs']} companies={d['total_companies']}")
        if d["jobs"]:
            j0 = d["jobs"][0]
            for field in ("latitude", "longitude", "company_name"):
                if j0.get(field) is None:
                    warn(f"search job[0].{field}", "None - required for map rendering")
    else:
        fail("GET /search", "missing jobs/companies keys")


def test_search_region(region: str, label: str):
    """Verify the search endpoint returns results when filtered by a specific region."""
    r = get("/search", {"region": region})
    d = r.json()
    n = d.get("total_jobs", 0)
    if n > 0:
        ok(f"region={region}", f"jobs={n} companies={d.get('total_companies')}")
    else:
        warn(f"region={region}", f"0 jobs - ingest a {label} company first")


def test_companies():
    """Verify company listing and detail endpoints return required fields."""
    section("10. Companies endpoint")
    r = get("/companies")
    d = r.json()
    total = d.get("total", 0)
    if total > 0:
        ok("GET /companies", f"total={total}")
        c0 = d["companies"][0]
        for field in ("slug", "latitude", "longitude"):
            if c0.get(field) is None:
                warn(f"company[0].{field}", "is None")
        slug = c0.get("slug")
        if slug:
            r2 = get(f"/companies/{slug}")
            if r2.status_code == 200:
                ok(f"GET /companies/{slug}", f"job_count={r2.json().get('job_count')}")
            else:
                fail(f"GET /companies/{slug}", f"status={r2.status_code}")
    else:
        warn("GET /companies", "no companies")


def test_stats():
    """Verify the stats endpoint returns non-zero counts and expected breakdown fields."""
    section("11. Stats endpoint")
    r = get("/stats")
    d = r.json()
    if r.status_code == 200:
        ok(
            "GET /stats",
            f"companies={d.get('total_companies')} active_jobs={d.get('active_jobs')} "
            f"cities_with_jobs={d.get('cities_with_jobs')}",
        )
        if d.get("top_regions"):
            ok("  top_regions", str(d["top_regions"][:3]))
        if d.get("ats_breakdown"):
            ok("  ats_breakdown", str(d["ats_breakdown"]))
    else:
        fail("GET /stats", f"status={r.status_code}")


def test_data_quality():
    """Audit a sample of jobs for coordinate coverage, source URLs, and role classification."""
    section("12. Data quality audit")
    r = get("/jobs", {"limit": 100})
    jobs: list[dict[str, Any]] = r.json().get("jobs", [])
    if not jobs:
        warn("Data quality", "no jobs to audit")
        return

    n = len(jobs)
    missing_lat = sum(1 for j in jobs if j.get("latitude") is None)
    missing_src = sum(1 for j in jobs if not j.get("source_url"))
    missing_role = sum(1 for j in jobs if not j.get("role_category"))

    def pct(x: int) -> str:
        return f"{x}/{n} ({100 * x // n}%)"

    if missing_lat == 0:
        ok("lat/lng coverage", f"100% (n={n})")
    elif missing_lat / n < 0.6:
        warn("lat/lng coverage", pct(missing_lat) + " missing (remote/vague locations)")
    else:
        fail(
            "lat/lng coverage",
            pct(missing_lat) + " missing - normalizer may have a bug",
        )

    if missing_src == 0:
        ok("source_url coverage", "100%")
    else:
        warn("Missing source_url", pct(missing_src))

    if missing_role == 0:
        ok("role_category coverage", "100%")
    else:
        warn("Missing role_category", pct(missing_role))

    ats_counts: dict[str, int] = {}
    for j in jobs:
        ats = j.get("ats_type", "unknown")
        ats_counts[ats] = ats_counts.get(ats, 0) + 1
    ok("ATS breakdown (sample)", str(ats_counts))


# Main


def main():
    """Parse CLI arguments and run the full integration validation suite."""
    global BASE
    parser = argparse.ArgumentParser(description="JobDex integration validator")
    parser.add_argument("--base-url", default=BASE)
    args = parser.parse_args()
    BASE = args.base_url.rstrip("/")

    print("\nJobDex Integration Validator")
    print(f"Target: {BASE}")
    print(f"{'=' * 60}")

    test_health()
    test_root()
    test_cities()

    test_jobs_list()
    test_city_alias()
    test_search()

    section("7. Region filter: South Asia")
    test_search_region("south_asia", "Indian")

    section("8. Region filter: Middle East")
    test_search_region("middle_east", "Middle Eastern")

    section("9. Search role=engineering")
    r = get("/search", {"role": "engineering"})
    d = r.json()
    ok("GET /search?role=engineering", f"jobs={d.get('total_jobs', 0)}")

    test_companies()
    test_stats()
    test_data_quality()

    print(f"\n{'=' * 60}")
    print(f"  Results: {len(errors)} errors   {len(warnings)} warnings")
    if errors:
        print("\n  Errors:")
        for e in errors:
            print(f"    {FAIL} {e}")
    if warnings:
        print("\n  Warnings:")
        for w in warnings:
            print(f"    {WARN} {w}")
    print(f"{'=' * 60}\n")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
