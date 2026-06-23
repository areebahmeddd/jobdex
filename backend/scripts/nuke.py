"""Drop all tables and reset the database to a clean state.

Usage:
  python scripts/nuke.py
"""

import sys

from sqlalchemy import text

from app.database import engine


def main() -> None:
    """Prompt for confirmation then drop all tables including the Alembic version tracker."""
    print("WARNING: This will permanently drop all tables in the database.")
    print(f"  Target: {engine.url}\n")
    answer = input("Type 'yes' to confirm: ").strip().lower()
    if answer != "yes":
        print("Aborted.")
        sys.exit(0)

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS jobs CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS cities CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS companies CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))

    print("Done. Run the server to re-apply migrations and re-seed cities.")


if __name__ == "__main__":
    main()
