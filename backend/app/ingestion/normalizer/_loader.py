import json

from app.config import DATA_DIR


def _load(filename: str) -> dict:
    """Load and return a JSON file from the data directory."""
    path = DATA_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)
