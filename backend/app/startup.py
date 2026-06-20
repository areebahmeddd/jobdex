import re
import unicodedata

from loguru import logger

from app.database import get_session
from app.ingestion.normalizer import get_city_data, get_featured_cities
from app.models import City


def _slugify(name: str) -> str:
    """Convert a city name to a URL-safe ASCII slug."""
    normalized = unicodedata.normalize("NFKD", name.lower())
    ascii_slug = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_slug).strip("-")


def seed_cities() -> None:
    """Seed the city table from data/cities.json, skipping cities that already exist."""
    city_data = get_city_data()
    featured = set(get_featured_cities())
    with get_session() as db:
        added = 0
        for name, info in city_data.items():
            slug = _slugify(name)
            if not db.query(City).filter(City.slug == slug).first():
                db.add(
                    City(
                        name=name,
                        slug=slug,
                        country=info["country"],
                        country_code=info["country_code"],
                        region=info.get("region", "").lower().replace(" ", "_") or None,
                        latitude=info["lat"],
                        longitude=info["lng"],
                        is_featured=name in featured,
                    )
                )
                added += 1
        db.commit()
        logger.info(f"Seeded {added} new cities")
