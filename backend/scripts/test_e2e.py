"""End-to-end test suite for the JobDex API.

Covers the full user flow: health, cities, map, companies, jobs, search.
Run after seeding:
  python scripts/test_e2e.py [--base-url http://127.0.0.1:8000]

Exit code 0 = all passed, 1 = one or more failures.
"""

import argparse
import sys
import time
from typing import Any

import httpx

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SECTION = "\033[94m"
RESET = "\033[0m"


class Runner:
    def __init__(self, base: str) -> None:
        """Initialize the test runner with the target API base URL."""
        self.base = base.rstrip("/")
        self.passed = 0
        self.failed = 0
        self.errors: list[str] = []

    def section(self, title: str) -> None:
        """Print a formatted section header to the console."""
        print(f"\n{SECTION}{'=' * 60}{RESET}")
        print(f"{SECTION}  {title}{RESET}")
        print(f"{SECTION}{'=' * 60}{RESET}")

    def check(self, label: str, cond: bool, detail: str = "") -> None:
        """Record a pass or fail for a single assertion and print the result."""
        if cond:
            self.passed += 1
            print(f"  {PASS}  {label}")
        else:
            self.failed += 1
            msg = label + (f" -- {detail}" if detail else "")
            self.errors.append(msg)
            print(f"  {FAIL}  {label}" + (f"\n         {detail}" if detail else ""))

    def get(self, path: str, params: dict | None = None) -> tuple[int, Any]:
        """Send a GET request to the API and return (status_code, parsed_body)."""
        try:
            r = httpx.get(f"{self.base}{path}", params=params, timeout=20.0)
            try:
                return r.status_code, r.json()
            except Exception:
                return r.status_code, r.text
        except Exception as exc:
            return 0, str(exc)

    def post(self, path: str, headers: dict | None = None) -> tuple[int, Any]:
        """Send a POST request to the API and return (status_code, parsed_body)."""
        try:
            r = httpx.post(f"{self.base}{path}", headers=headers or {}, timeout=30.0)
            try:
                return r.status_code, r.json()
            except Exception:
                return r.status_code, r.text
        except Exception as exc:
            return 0, str(exc)

    # ------------------------------------------------------------------
    def test_health(self) -> None:
        """Test the health and root metadata endpoints."""
        self.section("1. Health & Metadata")
        status, body = self.get("/health")
        self.check("GET /health returns 200", status == 200, str(body))
        self.check(
            "health status=ok", isinstance(body, dict) and body.get("status") == "ok", str(body)
        )

        status, body = self.get("/")
        self.check("GET / returns 200", status == 200, str(body))
        self.check("root has name field", isinstance(body, dict) and "name" in body, str(body))

    # ------------------------------------------------------------------
    def test_admin_stats(self) -> None:
        """Test the admin stats endpoint for required fields and non-zero counts."""
        self.section("2. Admin -- Stats")
        status, body = self.get("/admin/stats")
        self.check("GET /admin/stats returns 200", status == 200, str(body))
        if status == 200:
            self.check(
                "stats.total_jobs > 0", body.get("total_jobs", 0) > 0, str(body.get("total_jobs"))
            )
            self.check(
                "stats.active_jobs > 0",
                body.get("active_jobs", 0) > 0,
                str(body.get("active_jobs")),
            )
            self.check(
                "stats.role_categories is dict", isinstance(body.get("role_categories"), dict)
            )
            self.check("stats.top_cities is list", isinstance(body.get("top_cities"), list))
            self.check("stats.top_regions is list", isinstance(body.get("top_regions"), list))
            self.check("stats.ats_breakdown is dict", isinstance(body.get("ats_breakdown"), dict))

    # ------------------------------------------------------------------
    def test_cities(self) -> None:
        """Test city listing, filtering, pagination, and detail endpoints."""
        self.section("3. Cities")

        status, body = self.get("/cities")
        self.check("GET /cities returns 200", status == 200, str(body))
        if status == 200:
            self.check(
                "cities envelope present",
                "cities" in body and "total" in body,
                str(list(body.keys())),
            )
            self.check("cities total >= 135", body.get("total", 0) >= 135, str(body.get("total")))
            self.check("cities list non-empty", len(body.get("cities", [])) > 0)
            if body.get("cities"):
                c = body["cities"][0]
                self.check(
                    "city has required fields",
                    all(k in c for k in ["id", "name", "slug", "latitude", "longitude"]),
                    str(list(c.keys())),
                )

        status, body = self.get("/cities", params={"featured_only": "true"})
        self.check(
            "GET /cities?featured_only=true has results",
            status == 200 and len(body.get("cities", [])) > 0,
        )

        status, body = self.get("/cities", params={"region": "north_america"})
        self.check(
            "GET /cities?region=north_america filters correctly",
            status == 200
            and all(c.get("region") == "north_america" for c in body.get("cities", [])),
        )

        status, body = self.get("/cities/san-francisco")
        self.check("GET /cities/san-francisco returns 200", status == 200, str(body))
        if status == 200:
            self.check(
                "city slug matches", body.get("slug") == "san-francisco", str(body.get("slug"))
            )

        status, _ = self.get("/cities/does-not-exist-xyz")
        self.check("GET /cities/nonexistent returns 404", status == 404)

        # pagination
        _, body1 = self.get("/cities", params={"limit": 10, "offset": 0})
        _, body2 = self.get("/cities", params={"limit": 10, "offset": 10})
        p1 = body1.get("cities", [])
        p2 = body2.get("cities", [])
        self.check(
            "cities pagination pages don't overlap",
            len(p1) > 0 and len(p2) > 0 and p1[0]["slug"] != p2[0]["slug"],
        )

    # ------------------------------------------------------------------
    def test_map_companies(self) -> None:
        """Test map company pins including bbox, role, and country filters."""
        self.section("4. Map -- Company Pins")

        status, body = self.get("/map/companies")
        self.check("GET /map/companies returns 200", status == 200, str(body))
        if status != 200:
            return
        companies = body.get("companies", [])
        self.check("map/companies non-empty", len(companies) >= 1, str(len(companies)))
        if companies:
            c = companies[0]
            self.check(
                "pin has lat/lng",
                c.get("latitude") is not None and c.get("longitude") is not None,
                str(c),
            )
            self.check("pin job_count > 0", c.get("job_count", 0) > 0, str(c.get("job_count")))
            self.check("pin has slug", bool(c.get("slug")))

        # bbox -- SF area
        status, body = self.get(
            "/map/companies",
            params={"lat_min": 37.2, "lat_max": 37.9, "lng_min": -122.6, "lng_max": -122.0},
        )
        self.check("map/companies SF bbox returns 200", status == 200)
        if status == 200:
            self.check("map/companies SF bbox has results", len(body.get("companies", [])) >= 1)

        # role filter narrows job_count
        _, all_body = self.get("/map/companies")
        status_e, eng_body = self.get("/map/companies", params={"role": "engineering"})
        self.check("map/companies role=engineering returns 200", status_e == 200)
        if status_e == 200:
            all_map = {c["slug"]: c["job_count"] for c in all_body.get("companies", [])}
            for c in eng_body.get("companies", []):
                if c["slug"] in all_map:
                    self.check(
                        f"  {c['slug']} eng count <= total count",
                        c["job_count"] <= all_map[c["slug"]],
                        f"eng={c['job_count']} total={all_map[c['slug']]}",
                    )
                    break

        # country filter
        status, body = self.get("/map/companies", params={"country_code": "US"})
        self.check("map/companies country_code=US returns 200", status == 200)
        if status == 200:
            self.check("map/companies US has results", len(body.get("companies", [])) >= 1)

    # ------------------------------------------------------------------
    def test_map_cities(self) -> None:
        """Test map city cluster pins including bbox and role filters."""
        self.section("5. Map -- City Clusters")

        status, body = self.get("/map/cities")
        self.check("GET /map/cities returns 200", status == 200, str(body))
        if status != 200:
            return
        cities = body.get("cities", [])
        self.check("map/cities non-empty", len(cities) >= 1)
        if cities:
            self.check(
                "city cluster has job_count", "job_count" in cities[0], str(list(cities[0].keys()))
            )
            self.check("city cluster has company_count", "company_count" in cities[0])

        # bbox filter -- North America
        status, body = self.get(
            "/map/cities",
            params={"lat_min": 25.0, "lat_max": 50.0, "lng_min": -130.0, "lng_max": -60.0},
        )
        self.check("map/cities NA bbox returns 200", status == 200)
        if status == 200:
            na = body.get("cities", [])
            self.check("map/cities NA bbox has results", len(na) >= 1)
            if na:
                self.check(
                    "all returned cities within lat bbox",
                    all(25.0 <= c["latitude"] <= 50.0 for c in na if c.get("latitude") is not None),
                )

        # role filter
        status, _ = self.get("/map/cities", params={"role": "engineering"})
        self.check("map/cities role=engineering returns 200", status == 200)

    # ------------------------------------------------------------------
    def test_jobs(self) -> None:
        """Test job listing, filters, pagination, full-text search, and detail endpoints."""
        self.section("6. Jobs -- Listing & Filters")

        status, body = self.get("/jobs")
        self.check("GET /jobs returns 200", status == 200, str(body))
        if status == 200:
            self.check("jobs envelope present", "jobs" in body, str(list(body.keys())))
            self.check("jobs total > 0", (body.get("total") or 0) > 0, str(body.get("total")))
            self.check("jobs list non-empty", len(body.get("jobs", [])) > 0)
            if body.get("jobs"):
                j = body["jobs"][0]
                self.check(
                    "job has required fields",
                    all(k in j for k in ["id", "title", "source_url", "location_display"]),
                    str(list(j.keys())),
                )

        # city filter
        status, body = self.get("/jobs", params={"city": "San Francisco"})
        self.check("GET /jobs?city=San Francisco returns 200", status == 200)
        if status == 200:
            sf_jobs = body.get("jobs", [])
            self.check(
                "SF jobs all have city=San Francisco",
                all(j.get("city") == "San Francisco" for j in sf_jobs) if sf_jobs else True,
                str([j.get("city") for j in sf_jobs[:3]]),
            )

        # role filter
        status, body = self.get("/jobs", params={"role_category": "engineering"})
        self.check("GET /jobs?role_category=engineering returns 200", status == 200)
        if status == 200:
            eng = body.get("jobs", [])
            self.check(
                "engineering jobs have correct role_category",
                all(j.get("role_category") == "engineering" for j in eng) if eng else True,
            )

        # remote filter
        status, _ = self.get("/jobs", params={"is_remote": "true"})
        self.check("GET /jobs?is_remote=true returns 200", status == 200)

        # offset pagination
        _, b1 = self.get("/jobs", params={"limit": 10, "offset": 0})
        _, b2 = self.get("/jobs", params={"limit": 10, "offset": 10})
        self.check(
            "jobs offset pagination returns different pages",
            b1.get("jobs", [{}])[0].get("id") != b2.get("jobs", [{}])[0].get("id")
            if b1.get("jobs") and b2.get("jobs")
            else False,
        )

        # cursor pagination
        status, body = self.get("/jobs", params={"limit": 5})
        self.check(
            "GET /jobs limit=5 returns next_cursor",
            status == 200 and body.get("next_cursor") is not None,
        )
        if status == 200 and body.get("next_cursor"):
            cursor = body["next_cursor"]
            status2, body2 = self.get("/jobs", params={"cursor": cursor, "limit": 5})
            self.check("cursor second page returns 200", status2 == 200)
            if status2 == 200:
                p1_ids = {j["id"] for j in body.get("jobs", [])}
                p2_ids = {j["id"] for j in body2.get("jobs", [])}
                self.check(
                    "cursor pages don't overlap", len(p1_ids & p2_ids) == 0, str(p1_ids & p2_ids)
                )

        # FTS
        status, body = self.get("/jobs", params={"q": "engineer"})
        self.check("GET /jobs?q=engineer (FTS) returns 200", status == 200)
        if status == 200:
            self.check(
                "FTS returns results", len(body.get("jobs", [])) >= 1, str(body.get("total"))
            )

        # job detail
        status, body = self.get("/jobs")
        if status == 200 and body.get("jobs"):
            job_id = body["jobs"][0]["id"]
            status2, body2 = self.get(f"/jobs/{job_id}")
            self.check("GET /jobs/{id} returns 200", status2 == 200, str(body2))
            if status2 == 200:
                self.check("job detail has description field", "description" in body2)

        status, _ = self.get("/jobs/nonexistent-id-xyz")
        self.check("GET /jobs/nonexistent returns 404", status == 404)

    # ------------------------------------------------------------------
    def test_companies(self) -> None:
        """Test company listing, detail, per-company job listing, and filter endpoints."""
        self.section("7. Companies -- Listing, Detail, Jobs")

        status, body = self.get("/companies")
        self.check("GET /companies returns 200", status == 200, str(body))
        if status == 200:
            companies = body.get("companies", [])
            self.check("companies envelope present", "companies" in body and "total" in body)
            self.check("companies list non-empty", len(companies) >= 1, str(len(companies)))
            if companies:
                c = companies[0]
                self.check(
                    "company has required fields",
                    all(k in c for k in ["id", "slug", "name", "job_count"]),
                    str(list(c.keys())),
                )

        # detail
        status, body = self.get("/companies/airbnb")
        self.check("GET /companies/airbnb returns 200", status == 200, str(body))
        if status == 200:
            self.check("airbnb job_count > 0", body.get("job_count", 0) > 0)
            self.check(
                "airbnb open_role_categories is list",
                isinstance(body.get("open_role_categories"), list),
            )
            self.check(
                "airbnb detail has no embedded jobs list",
                "jobs" not in body or body.get("jobs") is None,
                "jobs key present in detail response",
            )

        status, _ = self.get("/companies/no-such-company-xyz")
        self.check("GET /companies/nonexistent returns 404", status == 404)

        # company jobs
        status, body = self.get("/companies/airbnb/jobs")
        self.check("GET /companies/airbnb/jobs returns 200", status == 200, str(body))
        if status == 200:
            self.check("airbnb jobs envelope", "jobs" in body and "total" in body)
            self.check("airbnb jobs total > 0", body.get("total", 0) > 0)
            jobs = body.get("jobs", [])
            if jobs:
                self.check("company job has location_display", "location_display" in jobs[0])

        # company jobs city filter
        status, body = self.get("/companies/airbnb/jobs", params={"city": "San Francisco"})
        self.check("GET /companies/airbnb/jobs?city=San Francisco returns 200", status == 200)
        if status == 200:
            sf = body.get("jobs", [])
            self.check(
                "airbnb SF jobs all have city=San Francisco",
                all(j.get("city") == "San Francisco" for j in sf) if sf else True,
            )

        # company jobs role filter
        status, _ = self.get("/companies/airbnb/jobs", params={"role_category": "engineering"})
        self.check(
            "GET /companies/airbnb/jobs?role_category=engineering returns 200", status == 200
        )

        # listing filter
        status, _ = self.get("/companies", params={"country_code": "US"})
        self.check("GET /companies?country_code=US returns 200", status == 200)

        # listing pagination
        _, b1 = self.get("/companies", params={"limit": 3, "offset": 0})
        _, b2 = self.get("/companies", params={"limit": 3, "offset": 3})
        c1 = b1.get("companies", [])
        c2 = b2.get("companies", [])
        self.check(
            "companies pagination returns different pages",
            len(c1) > 0 and (not c2 or c1[0]["slug"] != c2[0]["slug"]),
        )

    # ------------------------------------------------------------------
    def test_search(self) -> None:
        """Test the cross-entity search endpoint with single and combined filters."""
        self.section("8. Search -- Cross-Entity Discovery")

        status, body = self.get("/search")
        self.check("GET /search returns 200", status == 200, str(body))
        if status == 200:
            self.check(
                "search has all expected keys",
                all(
                    k in body
                    for k in ["jobs", "companies", "total_jobs", "total_companies", "offset"]
                ),
                str(list(body.keys())),
            )
            self.check("search total_jobs > 0", body.get("total_jobs", 0) > 0)

        # city filter
        status, body = self.get("/search", params={"city": "San Francisco"})
        self.check("GET /search?city=San Francisco returns 200", status == 200)
        if status == 200:
            jobs = body.get("jobs", [])
            self.check(
                "search SF city: all jobs have city=SF",
                all(j.get("city") == "San Francisco" for j in jobs) if jobs else True,
            )

        # role filter
        status, body = self.get("/search", params={"role": "engineering"})
        self.check("GET /search?role=engineering returns 200", status == 200)
        if status == 200:
            jobs = body.get("jobs", [])
            self.check(
                "search role=engineering: jobs have correct category",
                all(j.get("role_category") == "engineering" for j in jobs) if jobs else True,
            )

        # combined filter
        status, _ = self.get("/search", params={"city": "New York", "role": "engineering"})
        self.check("GET /search city+role combined returns 200", status == 200)

        # region filter
        status, _ = self.get("/search", params={"region": "north_america"})
        self.check("GET /search?region=north_america returns 200", status == 200)

        # offset pagination
        _, b1 = self.get("/search", params={"limit": 10, "offset": 0})
        _, b2 = self.get("/search", params={"limit": 10, "offset": 10})
        j1 = b1.get("jobs", [])
        j2 = b2.get("jobs", [])
        self.check(
            "search offset pagination returns different pages",
            not j1 or not j2 or j1[0]["id"] != j2[0]["id"],
        )
        self.check(
            "search response has offset field, not page",
            "offset" in b1 and "page" not in b1 if isinstance(b1, dict) else False,
            str(list(b1.keys())) if isinstance(b1, dict) else "",
        )

        # industry filter
        status, _ = self.get("/search", params={"industry": "saas"})
        self.check("GET /search?industry=saas returns 200", status == 200)

    # ------------------------------------------------------------------
    def test_user_flow(self) -> None:
        """Simulate the end-to-end user journey from globe view to job detail."""
        self.section("9. Simulated User Flow -- Globe to Job Detail")

        print("  Step 1: Load globe -- all company pins")
        status, body = self.get("/map/companies")
        globe_ok = status == 200 and len(body.get("companies", [])) >= 1
        self.check("globe loads company pins", globe_ok)
        if not globe_ok:
            return
        companies = body["companies"]

        target = next((c for c in companies if c["slug"] == "airbnb"), companies[0])
        lat, lng, slug, name = (
            target["latitude"],
            target["longitude"],
            target["slug"],
            target["name"],
        )

        print(f"  Step 2: Zoom bbox around {name} ({lat:.2f}, {lng:.2f})")
        delta = 2.0
        status, bbox = self.get(
            "/map/companies",
            params={
                "lat_min": lat - delta,
                "lat_max": lat + delta,
                "lng_min": lng - delta,
                "lng_max": lng + delta,
            },
        )
        self.check(
            f"bbox around {name} has results", status == 200 and len(bbox.get("companies", [])) >= 1
        )

        print(f"  Step 3: Click {name} -- company detail")
        status, detail = self.get(f"/companies/{slug}")
        self.check(f"company detail for {name}", status == 200 and detail.get("job_count", 0) > 0)

        print(f"  Step 4: Load {name} jobs")
        status, jobs_body = self.get(f"/companies/{slug}/jobs")
        self.check(f"company jobs for {name}", status == 200 and jobs_body.get("total", 0) > 0)
        job_list = jobs_body.get("jobs", [])

        if job_list:
            print(f"  Step 5: Open job detail for '{job_list[0]['title']}'")
            status, job_detail = self.get(f"/jobs/{job_list[0]['id']}")
            self.check("job detail loads", status == 200)
            self.check("job detail has source_url", bool(job_detail.get("source_url")))

        print(f"  Step 6: Filter {name} jobs by city")
        status, _ = self.get(f"/companies/{slug}/jobs", params={"city": "San Francisco"})
        self.check(f"{name} jobs filtered by city returns 200", status == 200)

        print("  Step 7: Switch to map city clusters")
        status, body = self.get("/map/cities")
        self.check("city clusters load", status == 200 and len(body.get("cities", [])) >= 1)
        cities_with_jobs = [c for c in body.get("cities", []) if c.get("job_count", 0) > 0]
        self.check("at least one city cluster has jobs", len(cities_with_jobs) >= 1)

        if cities_with_jobs:
            top_city = cities_with_jobs[0]
            city_name = top_city["name"]
            city_slug = top_city["slug"]
            print(f"  Step 8: City detail for {city_name}")
            status, city_detail = self.get(f"/cities/{city_slug}")
            self.check(f"city detail for {city_name}", status == 200)
            if status == 200:
                self.check(f"{city_name} has job_count field", "job_count" in city_detail)

            print(f"  Step 9: Search engineering in {city_name}")
            status, _ = self.get("/search", params={"city": city_name, "role": "engineering"})
            self.check(f"search city={city_name} role=engineering", status == 200)

    # ------------------------------------------------------------------
    def test_coordinates(self) -> None:
        """Verify that all company map pins have valid lat/lng coordinate ranges."""
        self.section("10. Coordinate Correctness")
        status, body = self.get("/map/companies")
        if status != 200:
            return
        for c in body.get("companies", []):
            if c.get("latitude") is not None:
                self.check(
                    f"{c['name']} lat in [-90, 90]",
                    -90 <= c["latitude"] <= 90,
                    str(c["latitude"]),
                )
                self.check(
                    f"{c['name']} lng in [-180, 180]",
                    -180 <= c["longitude"] <= 180,
                    str(c["longitude"]),
                )

    # ------------------------------------------------------------------
    def run_all(self) -> int:
        """Run the full test suite and return 0 on success or 1 if any test failed."""
        print("\nJobDex E2E Test Suite")
        print(f"Target: {self.base}")
        print("=" * 60)

        self.test_health()
        self.test_admin_stats()
        self.test_cities()
        self.test_map_companies()
        self.test_map_cities()
        self.test_jobs()
        self.test_companies()
        self.test_search()
        self.test_user_flow()
        self.test_coordinates()

        time.sleep(0.1)
        self.section("SUMMARY")
        total = self.passed + self.failed
        print(f"\n  Total  : {total}")
        print(f"  {PASS}  Passed : {self.passed}")
        if self.failed:
            print(f"  {FAIL}  Failed : {self.failed}")
            print()
            for i, e in enumerate(self.errors, 1):
                print(f"    {i}. {e}")
        else:
            print("  No failures.")
        score = round(100 * self.passed / total) if total else 0
        print(f"\n  Score: {score}%\n")
        return 0 if self.failed == 0 else 1


def main() -> None:
    """Parse CLI arguments and run the full E2E test suite against the target API."""
    parser = argparse.ArgumentParser(description="JobDex E2E test suite")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    args = parser.parse_args()
    sys.exit(Runner(args.base_url).run_all())


if __name__ == "__main__":
    main()
