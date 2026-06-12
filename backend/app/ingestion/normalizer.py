from __future__ import annotations

import json
import re

import httpx
from loguru import logger

from app.config import DATA_DIR, settings


def _load(filename: str) -> dict:
    """Load and return a JSON file from the data directory."""
    path = DATA_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_cities_cfg = _load("cities.json")
_role_cfg = _load("role_patterns.json")
_seniority_cfg = _load("seniority_patterns.json")
_tech_cfg = _load("tech_keywords.json")

_city_data: dict[str, dict] = _cities_cfg["cities"]
_city_aliases: dict[str, str] = {k.lower(): v for k, v in _cities_cfg["aliases"].items()}
_regions_map: dict[str, list] = _cities_cfg["regions"]
_featured_cities: list[str] = _cities_cfg["featured"]

_role_patterns: list[dict] = _role_cfg["patterns"]
_seniority_patterns: list[dict] = _seniority_cfg["patterns"]
_tech_keywords: list[str] = _tech_cfg["keywords"]
_job_type_map: dict[str, str] = _tech_cfg["job_type_map"]

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


def get_city_data() -> dict[str, dict]:
    """Return the full city metadata dictionary keyed by canonical city name."""
    return _city_data


def get_featured_cities() -> list[str]:
    """Return the list of featured city names used for map highlights."""
    return _featured_cities


def canonicalize_city(name: str) -> str | None:
    """Return the canonical city name for the input string, or None if unrecognised."""
    lowered = name.lower().strip()
    if lowered in _city_aliases:
        return _city_aliases[lowered]
    for city_name in _city_data:
        if city_name.lower() == lowered:
            return city_name
    # Partial: input is a substring of a known city or vice-versa
    for city_name in _city_data:
        if lowered in city_name.lower() or city_name.lower() in lowered:
            return city_name
    return None


def get_region_for_country(country_code: str) -> str | None:
    """Return the region identifier for the given ISO-2 country code, or None if not mapped."""
    for region, codes in _regions_map.items():
        if country_code.upper() in codes:
            return region
    return None


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
        # Anchor to company HQ for map coordinates.
        _apply_city(result, fallback_city)
        if not result["country_code"] and fallback_country_code:
            result["country_code"] = fallback_country_code
        return result
    elif is_remote:
        result["is_remote"] = True
        result["remote_type"] = "hybrid"

    # 1. Alias lookup.
    canonical = _city_aliases.get(lowered)
    if canonical and canonical in _city_data:
        return {**result, **_city_fields(canonical)}

    # 2. Exact full-string match.
    for city_name in _city_data:
        if city_name.lower() == lowered:
            return {**result, **_city_fields(city_name)}

    # 3. City name contained anywhere in string.
    for city_name in _city_data:
        if city_name.lower() in lowered:
            return {**result, **_city_fields(city_name)}

    # 4. First comma-part match.
    first_part = raw.split(",")[0].strip()
    first_lower = first_part.lower()
    canonical = _city_aliases.get(first_lower)
    if canonical and canonical in _city_data:
        return {**result, **_city_fields(canonical)}
    for city_name in _city_data:
        if city_name.lower() == first_lower:
            return {**result, **_city_fields(city_name)}

    # 5. Optional geocoding via Nominatim.
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

    # 6. Fall back to company HQ.
    _apply_city(result, fallback_city)
    if not result["country_code"] and fallback_country_code:
        result["country_code"] = fallback_country_code
        result["region"] = get_region_for_country(fallback_country_code)
    return result


def classify_seniority(title: str) -> str:
    """Return the seniority level for a job title based on pattern matching."""
    lowered = title.lower()
    for entry in _seniority_patterns:
        for pat in entry["patterns"]:
            if re.search(pat, lowered):
                return entry["level"]
    return "mid"


def classify_role(
    title: str,
    description: str = "",
    department: str = "",
) -> tuple[str, str]:
    """Return a (category, subcategory) tuple for a job based on title, department, and description."""
    search_text = f"{title} {department}".lower()
    desc_text = description.lower()[:400]
    for entry in _role_patterns:
        for pat in entry["patterns"]:
            if re.search(pat, search_text):
                return entry["category"], entry["subcategory"]
    for entry in _role_patterns:
        for pat in entry["patterns"]:
            if re.search(pat, desc_text):
                return entry["category"], entry["subcategory"]
    return "other", "general"


def extract_tech_stack(title: str, description: str = "") -> list[str]:
    """Return a sorted list of tech keywords found in the title and description."""
    combined = f"{title} {description}".lower()
    found = set()
    for kw in _tech_keywords:
        escaped = re.escape(kw)
        if re.search(rf"(?<!\w){escaped}(?!\w)", combined):
            found.add(kw)
    return sorted(found)


def normalize_job_type(raw: str) -> str | None:
    """Map a raw employment type string to a normalized job type, or None if not recognized."""
    return _job_type_map.get(raw.lower().strip()) if raw else None


def strip_html(html: str) -> str:
    """Strip HTML tags and decode common entities from a string, returning plain text."""
    if not html:
        return ""
    clean = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    entities = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&nbsp;": " ",
    }
    for ent, char in entities.items():
        clean = clean.replace(ent, char)
    return re.sub(r"\s+", " ", clean).strip()


def make_snippet(text: str, max_chars: int = 500) -> str:
    """Truncate plain text to max_chars at a word boundary and append an ellipsis if needed."""
    plain = strip_html(text)
    if len(plain) <= max_chars:
        return plain
    truncated = plain[:max_chars]
    last_space = truncated.rfind(" ")
    return (truncated[:last_space] if last_space > 0 else truncated) + "..."


# Private helpers


def _normalize_region(region: str | None) -> str | None:
    """Convert a region name to a lowercase underscore-separated identifier."""
    if not region:
        return None
    return region.lower().replace(" ", "_")


def _city_fields(city_name: str) -> dict:
    """Return the full location field dict for a known city name."""
    d = _city_data[city_name]
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
    for city_name in _city_data:
        if city_name.lower() in text:
            return True
    return False


def _apply_city(result: dict, city_name: str | None) -> None:
    """Populate location fields in result from the city data store if the city is known."""
    if city_name and city_name in _city_data:
        d = _city_data[city_name]
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
            logger.debug(f"Geocoded '{location}' -> {result}")
            return result
    except Exception as exc:
        logger.debug(f"Geocode failed for '{location}': {exc}")
    _geocode_cache[key] = None
    return None
