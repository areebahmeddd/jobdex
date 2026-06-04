from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _normalize_db_url(url: str) -> str:
    """Rewrite asyncpg-style database URLs to their psycopg2 equivalents."""
    url = url.replace("+asyncpg", "+psycopg2")
    if "sslmode" not in url:
        url = url.replace("ssl=require", "sslmode=require")
    return url


engine = create_engine(
    _normalize_db_url(settings.DATABASE_URL),
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=2,
    max_overflow=3,
    pool_timeout=30,
    pool_recycle=600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and indexes."""
    from app.models import City, Company, Job  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database ready")
