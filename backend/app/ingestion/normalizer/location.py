import re

import httpx2 as httpx
from loguru import logger

from app.config import settings
from app.ingestion.normalizer._loader import _load

_cities_cfg = _load("cities.json")

_CITY_DATA: dict[str, dict] = _cities_cfg["cities"]
_CITY_ALIASES: dict[str, str] = {k.lower(): v for k, v in _cities_cfg["aliases"].items()}
_REGIONS_MAP: dict[str, list] = _cities_cfg["regions"]
_FEATURED_CITIES: list[str] = _cities_cfg["featured"]

# Per-process geocode cache.
_geocode_cache: dict[str, tuple | None] = {}

# Remote/hybrid detection patterns.
_REMOTE_PATTERNS = [
    r"\bremote\b",
    r"\bwork from home\b",
    r"\bwfh\b",
    r"\banywhere\b",
    r"\bglobal\b",
    r"\bdistributed\b",
    r"\bworldwide\b",
]
_HYBRID_PATTERNS = [r"\bhybrid\b", r"\bflexible location\b", r"\bpartially remote\b"]

# Locations permanently excluded from the index.
_BLOCKED_COUNTRY_CODES: frozenset[str] = frozenset({"IL"})
_BLOCKED_CITY_SUBSTRINGS: tuple[str, ...] = (
    "israel",
    "tel aviv",
    "haifa",
    "beer sheva",
    "jerusalem",
)


def get_city_data() -> dict[str, dict]:
    """Return the full city metadata dictionary keyed by canonical city name."""
    return _CITY_DATA


def get_featured_cities() -> list[str]:
    """Return the list of featured city names used for map highlights."""
    return _FEATURED_CITIES


def canonicalize_city(name: str) -> str | None:
    """Return the canonical city name for the input string, or None if unrecognised."""
    lowered = name.lower().strip()
    if lowered in _CITY_ALIASES:
        return _CITY_ALIASES[lowered]
    for city_name in _CITY_DATA:
        if city_name.lower() == lowered:
            return city_name
    # Partial: input is a substring of a known city or vice-versa
    for city_name in _CITY_DATA:
        if lowered in city_name.lower() or city_name.lower() in lowered:
            return city_name
    return None


def get_region_for_country(country_code: str) -> str | None:
    """Return the region identifier for the given ISO-2 country code, or None if not mapped."""
    for region, codes in _REGIONS_MAP.items():
        if country_code.upper() in codes:
            return region
    return None


def is_blocked_location(country_code: str | None, city: str | None) -> bool:
    """Return True if the resolved location is in a permanently excluded country or city."""
    if country_code and country_code.upper() in _BLOCKED_COUNTRY_CODES:
        return True
    if city:
        city_lower = city.lower()
        return any(sub in city_lower for sub in _BLOCKED_CITY_SUBSTRINGS)
    return False


def normalize_location(
    location_raw: str,
    fallback_city: str | None = None,
    fallback_country_code: str | None = None,
) -> dict:
    """Resolve a raw location string to a normalized dict with city, coordinates, and remote flags."""
    result: dict = {
        "city": None,
        "country": None,
        "country_code": None,
        "region": None,
        "latitude": None,
        "longitude": None,
        "is_remote": False,
        "remote_type": "onsite",
    }

    raw = (location_raw or "").strip()
    lowered = raw.lower()

    is_hybrid = any(re.search(p, lowered) for p in _HYBRID_PATTERNS)
    is_remote = any(re.search(p, lowered) for p in _REMOTE_PATTERNS)

    if is_hybrid:
        result["is_remote"] = True
        result["remote_type"] = "hybrid"
    elif is_remote and not _has_known_city(lowered):
        result["is_remote"] = True
        result["remote_type"] = "fully-remote"
        _apply_city(result, fallback_city)
        if not result["country_code"] and fallback_country_code:
            result["country_code"] = fallback_country_code
        return result
    elif is_remote:
        result["is_remote"] = True
        result["remote_type"] = "hybrid"

    canonical = _CITY_ALIASES.get(lowered)
    if canonical and canonical in _CITY_DATA:
        return {**result, **_city_fields(canonical)}

    for city_name in _CITY_DATA:
        if city_name.lower() == lowered:
            return {**result, **_city_fields(city_name)}

    for city_name in _CITY_DATA:
        if city_name.lower() in lowered:
            return {**result, **_city_fields(city_name)}

    first_part = raw.split(",")[0].strip()
    first_lower = first_part.lower()
    canonical = _CITY_ALIASES.get(first_lower)
    if canonical and canonical in _CITY_DATA:
        return {**result, **_city_fields(canonical)}
    for city_name in _CITY_DATA:
        if city_name.lower() == first_lower:
            return {**result, **_city_fields(city_name)}

    if settings.GEOCODE_UNKNOWN_CITIES and raw:
        geo = _geocode(raw)
        if geo:
            lat, lng, cc, country = geo
            region = get_region_for_country(cc)
            return {
                **result,
                "city": first_part or raw,
                "country": country,
                "country_code": cc,
                "region": region,
                "latitude": lat,
                "longitude": lng,
            }

    _apply_city(result, fallback_city)
    if not result["country_code"] and fallback_country_code:
        result["country_code"] = fallback_country_code
        result["region"] = get_region_for_country(fallback_country_code)
    return result


# Private helpers


def _normalize_region(region: str | None) -> str | None:
    """Convert a region name to a lowercase underscore-separated identifier."""
    if not region:
        return None
    return region.lower().replace(" ", "_")


def _city_fields(city_name: str) -> dict:
    """Return the full location field dict for a known city name."""
    d = _CITY_DATA[city_name]
    return {
        "city": city_name,
        "country": d["country"],
        "country_code": d["country_code"],
        "region": _normalize_region(d.get("region")),
        "latitude": d["lat"],
        "longitude": d["lng"],
        "is_remote": False,
        "remote_type": "onsite",
    }


def _has_known_city(text: str) -> bool:
    """Return True if any known city name appears in the given text."""
    for city_name in _CITY_DATA:
        if city_name.lower() in text:
            return True
    return False


def _apply_city(result: dict, city_name: str | None) -> None:
    """Populate location fields in result from the city data store if the city is known."""
    if city_name and city_name in _CITY_DATA:
        d = _CITY_DATA[city_name]
        result.update(
            city=city_name,
            country=d["country"],
            country_code=d["country_code"],
            region=_normalize_region(d.get("region")),
            latitude=d["lat"],
            longitude=d["lng"],
        )


def _geocode(location: str) -> tuple | None:
    """Query Nominatim for coordinates of a location string, caching results per process."""
    key = location.lower().strip()
    if key in _geocode_cache:
        return _geocode_cache[key]
    try:
        r = httpx.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": location,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            },
            headers={"User-Agent": settings.GEOCODE_USER_AGENT},
            timeout=8.0,
        )
        data = r.json()
        if data:
            item = data[0]
            lat = float(item["lat"])
            lng = float(item["lon"])
            address = item.get("address", {})
            cc = address.get("country_code", "").upper()
            country = address.get("country", "")
            result = (lat, lng, cc, country)
            _geocode_cache[key] = result
            logger.debug(f"[geocode] '{location}' -> {result}")
            return result
    except Exception as exc:
        logger.debug(f"[geocode] failed for '{location}': {exc}")
    _geocode_cache[key] = None
    return None
