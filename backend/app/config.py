from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved at import time; independent of cwd.
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    APP_NAME: str = "JobDex API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "A global index of startup hiring by city"
    API_URL: str = "http://localhost:8000"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql://localhost/jobdex"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 2
    DB_MAX_OVERFLOW: int = 3
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 600

    HTTP_TIMEOUT: float = 30.0
    CRAWL_DELAY: float = 0.3

    INGEST_INTERVAL_HOURS: int = 6
    ENRICH_INTERVAL_HOURS: int = 12
    DISCOVER_INTERVAL_HOURS: int = 24

    GEOCODE_UNKNOWN_CITIES: bool = False
    GEOCODE_USER_AGENT: str = "JobDex/1.0 (+https://github.com/areebahmeddd/jobdex)"

    ENRICHMENT_BOT_AGENT: str = "JobDex/1.0 (+https://github.com/areebahmeddd/jobdex)"
    ENRICHMENT_REQUEST_TIMEOUT: float = 15.0
    ENRICHMENT_STEP_DELAY: float = 0.5
    ENRICH_REFRESH_DAYS: int = 90

    HTTP_RETRY_ATTEMPTS: int = 3
    HTTP_RETRY_MIN_WAIT: float = 2.0
    HTTP_RETRY_MAX_WAIT: float = 30.0

    ALLOWED_ORIGINS: list[str] = [
        "https://jobdex-api.1mindlabs.org",
        "https://jobdex.1mindlabs.org",
        "http://localhost:3000",
    ]

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""


settings = Settings()
