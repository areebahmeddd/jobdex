import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.database import engine
from app.main import app


@pytest.fixture(scope="session")
def client():
    """TestClient for the full FastAPI app. Skipped if the database is unavailable."""
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("Database not available — skipping integration tests")

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
