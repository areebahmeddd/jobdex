import re

from app.ingestion.normalizer._loader import _load

_ROLE_PATTERNS: list[dict] = _load("role_patterns.json")["patterns"]
_SENIORITY_PATTERNS: list[dict] = _load("seniority_patterns.json")["patterns"]
_tech_cfg = _load("tech_keywords.json")
_TECH_KEYWORDS: list[str] = _tech_cfg["keywords"]
_JOB_TYPE_MAP: dict[str, str] = _tech_cfg["job_type_map"]


def classify_seniority(title: str) -> str:
    """Return the seniority level for a job title based on pattern matching."""
    lowered = title.lower()
    for entry in _SENIORITY_PATTERNS:
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
    for entry in _ROLE_PATTERNS:
        for pat in entry["patterns"]:
            if re.search(pat, search_text):
                return entry["category"], entry["subcategory"]
    for entry in _ROLE_PATTERNS:
        for pat in entry["patterns"]:
            if re.search(pat, desc_text):
                return entry["category"], entry["subcategory"]
    return "other", "general"


def extract_tech_stack(title: str, description: str = "") -> list[str]:
    """Return a sorted list of tech keywords found in the title and description."""
    combined = f"{title} {description}".lower()
    found = set()
    for kw in _TECH_KEYWORDS:
        escaped = re.escape(kw)
        if re.search(rf"(?<!\w){escaped}(?!\w)", combined):
            found.add(kw)
    return sorted(found)


def normalize_job_type(raw: str) -> str | None:
    """Map a raw employment type string to a normalized job type, or None if not recognized."""
    return _JOB_TYPE_MAP.get(raw.lower().strip()) if raw else None
