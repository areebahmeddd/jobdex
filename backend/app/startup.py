import re
import unicodedata
import uuid

from loguru import logger
from sqlalchemy.dialects.postgresql import insert

from app.database import get_session
from app.ingestion.normalizer import get_city_data
from app.models import City


def _slugify(name: str) -> str:
    """Convert a city name to a URL-safe ASCII slug."""
    normalized = unicodedata.normalize("NFKD", name.lower())
    ascii_slug = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_slug).strip("-")


def seed_cities() -> None:
    """Seed the city table from data/cities.json, skipping cities that already exist.

    Uses a single ON CONFLICT DO NOTHING insert rather than check-then-insert: two
    replicas booting against an empty table would otherwise both pass the existence
    check and the loser would fail startup on the unique City.slug constraint.
    """
    rows = [
        {
            "id": str(uuid.uuid4()),
            "name": name,
            "slug": _slugify(name),
            "country": info["country"],
            "country_code": info["country_code"],
            "region": info.get("region", "").lower().replace(" ", "_") or None,
            "latitude": info["lat"],
            "longitude": info["lng"],
        }
        for name, info in get_city_data().items()
    ]
    if not rows:
        return

    with get_session() as db:
        result = db.execute(
            insert(City).values(rows).on_conflict_do_nothing(index_elements=["slug"])
        )
        db.commit()
        logger.info(f"Seeded {result.rowcount} new cities")
