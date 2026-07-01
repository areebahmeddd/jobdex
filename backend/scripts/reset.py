"""Reset all jobs and crawl state, keeping companies and cities intact.

Usage:
  python scripts/reset.py
"""

import sys

from app.database import get_session
from app.models import Company, Job


def main() -> None:
    """Prompt for confirmation then delete all jobs and reset company crawl state."""
    print("WARNING: This will delete ALL jobs and reset company crawl timestamps.")
    answer = input("Type 'yes' to confirm: ").strip().lower()
    if answer != "yes":
        print("Aborted.")
        sys.exit(0)

    with get_session() as db:
        deleted = db.query(Job).delete()
        db.query(Company).update({"last_crawled_at": None, "crawl_error": None})
        db.commit()

    print(f"Reset complete - {deleted} jobs deleted. Companies and cities retained.")


if __name__ == "__main__":
    main()
