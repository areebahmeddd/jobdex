from loguru import logger

from app.database import SessionLocal
from app.ingestion.normalizer import get_city_data, get_featured_cities
from app.models import City


def _slugify(name: str) -> str:
    """Convert a city name to a URL-safe ASCII slug."""
    return (
        name.lower()
        .replace(" ", "-")
        .replace("ã", "a")
        .replace("á", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("ú", "u")
        .replace("ü", "u")
        .replace("ç", "c")
    )


def seed_cities() -> None:
    """Seed the city table from data/cities.json, skipping cities that already exist."""
    city_data = get_city_data()
    featured = set(get_featured_cities())
    db = SessionLocal()
    try:
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
    finally:
        db.close()
