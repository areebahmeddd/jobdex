from collections.abc import Iterator
from contextlib import contextmanager

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _normalize_db_url(url: str) -> str:
    """Rewrite a PostgreSQL URL to a psycopg2-compatible form.

    - Injects +psycopg2 driver if absent
    - Replaces +asyncpg with +psycopg2
    - Rewrites ssl=require to sslmode=require
    - Strips channel_binding=require (unsupported by psycopg2)
    """
    if "://" in url and "+" not in url.split("://")[0]:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    url = url.replace("+asyncpg", "+psycopg2")
    if "sslmode" not in url:
        url = url.replace("ssl=require", "sslmode=require")
    url = url.replace("&channel_binding=require", "").replace("channel_binding=require&", "")
    return url


engine = create_engine(
    _normalize_db_url(settings.DATABASE_URL),
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


@contextmanager
def get_session():
    """Provide a database session as a context manager for non-request contexts."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db():
    """Yield a database session and ensure it is closed after each request."""
    with get_session() as db:
        yield db


# Advisory lock keys. Arbitrary but must stay stable and distinct across the codebase.
LOCK_MIGRATE = 881_100_1
LOCK_INGEST = 881_100_2
LOCK_ENRICH = 881_100_3
LOCK_DISCOVER = 881_100_4


@contextmanager
def advisory_lock(key: int, *, wait: bool = False) -> Iterator[bool]:
    """Hold a Postgres session-level advisory lock for the duration of the block.

    Yields True when the lock is held. With wait=False a lock already held by another
    instance yields False immediately, which is how the scheduler keeps concurrent
    replicas from running the same job. The lock must be released explicitly because
    closing a pooled connection returns it to the pool without ending the session.
    """
    conn = engine.connect()
    acquired = False
    try:
        if wait:
            conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": key})
            acquired = True
        else:
            acquired = bool(
                conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar()
            )
        yield acquired
    finally:
        if acquired:
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
        conn.close()


def migrate_db() -> None:
    """Apply all pending Alembic migrations to head.

    Serialised behind an advisory lock so concurrent replicas booting at the same time
    do not race on alembic_version. Whichever instance arrives second runs a no-op.
    """
    from alembic.config import Config

    from alembic import command
    from app.config import BASE_DIR

    cfg = Config(str(BASE_DIR / "alembic.ini"))
    with advisory_lock(LOCK_MIGRATE, wait=True):
        command.upgrade(cfg, "head")
    logger.info("Database migrations applied")
