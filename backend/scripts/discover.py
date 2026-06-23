"""Bulk-discover and register companies from all supported ingesters.

Usage:
  python scripts/discover.py
"""

import asyncio

from app.scheduler import run_discovery

if __name__ == "__main__":
    asyncio.run(run_discovery())
