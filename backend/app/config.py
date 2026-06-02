from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved at import time; independent of cwd.
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    APP_NAME: str = "JobDex API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql://localhost/jobdex"
    DB_ECHO: bool = False

    HTTP_TIMEOUT: float = 30.0
    CRAWL_DELAY: float = 0.3

    GEOCODE_UNKNOWN_CITIES: bool = False
    GEOCODE_USER_AGENT: str = "JobDex/1.0 (+https://github.com/areebahmeddd/jobdex.ai)"

    ADMIN_API_KEY: str | None = None


settings = Settings()
