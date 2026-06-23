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


settings = Settings()
