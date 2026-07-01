"""Bulk-discover and register companies from all supported ingesters.

Usage:
  python scripts/discover.py           # runs if no server is live
  python scripts/discover.py --force   # bypass server-live check
"""

import asyncio
import sys
import urllib.request

from loguru import logger

from app.config import settings
from app.ingestion import INGESTERS
from app.scheduler import run_discovery


def _abort_if_server_live(*, force: bool) -> None:
    """Exit with a warning when the API server is reachable and --force was not passed."""
    if force:
        return
    try:
        with urllib.request.urlopen(f"{settings.API_URL}/health", timeout=2) as r:
            if r.status == 200:
                print(
                    "\u26a0  A JobDex server is running. Concurrent scripts risk noisy dedup "
                    "errors and double ATS traffic.\n"
                    "   Stop the server first, or pass --force to proceed anyway."
                )
                sys.exit(1)
    except Exception:
        pass  # server not reachable; safe to proceed


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, format="  {message}", level="INFO", colorize=sys.stdout.isatty())

    _abort_if_server_live(force="--force" in sys.argv)

    sources = list(INGESTERS)
    print(f"\nJobDex Discovery - scanning {len(sources)} sources: {sources}")
    print(f"{'=' * 52}\n")

    asyncio.run(run_discovery())

    print(f"\n{'=' * 52}\n")
