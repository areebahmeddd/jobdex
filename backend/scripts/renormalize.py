"""Re-resolve locations for stored jobs whose city never matched.

Dedup means build_job() never re-runs for a stored posting, so a change to the city
table or the location rules leaves old rows as they were. This fills them in.

Only rows with no city are touched, and only from the raw string, never the company HQ
fallback, so nothing already resolved is overwritten and nothing inherits a wrong country.

Usage:
  python scripts/renormalize.py            # report what would change
  python scripts/renormalize.py --apply    # write the changes
"""

import sys

from app.database import get_session
from app.ingestion.normalizer import is_blocked_location, normalize_location
from app.models import Job


def main() -> None:
    """Report, and optionally apply, resolved locations for jobs that have no city."""
    apply = "--apply" in sys.argv

    with get_session() as db:
        rows = (
            db.query(Job)
            .filter(Job.is_active.is_(True), Job.city.is_(None), Job.location_raw.isnot(None))
            .all()
        )

        resolved: list[tuple[Job, dict]] = []
        blocked: list[Job] = []
        for job in rows:
            loc = normalize_location(job.location_raw)
            if not loc["city"]:
                continue
            if is_blocked_location(loc["country_code"], loc["city"]):
                blocked.append(job)
                continue
            resolved.append((job, loc))

        print(f"\njobs with no city : {len(rows)}")
        print(f"  now resolvable  : {len(resolved)}")
        print(f"  blocked location: {len(blocked)} (deactivated)")

        counts: dict[str, int] = {}
        for _, loc in resolved:
            counts[loc["city"]] = counts.get(loc["city"], 0) + 1
        for city, n in sorted(counts.items(), key=lambda kv: -kv[1])[:15]:
            print(f"     {city:24} {n}")

        if not apply:
            print("\nDry run. Re-run with --apply to write these changes.\n")
            return

        for job, loc in resolved:
            job.city = loc["city"]
            job.country = loc["country"]
            job.country_code = loc["country_code"]
            job.region = loc["region"]
            job.latitude = loc["latitude"]
            job.longitude = loc["longitude"]
        for job in blocked:
            job.is_active = False

        db.commit()
        print(f"\nupdated {len(resolved)} jobs, deactivated {len(blocked)}\n")


if __name__ == "__main__":
    main()
