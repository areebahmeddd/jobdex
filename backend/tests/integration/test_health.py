import pytest


@pytest.mark.integration
def test_health(client):
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.integration
def test_root(client):
    data = client.get("/").json()
    assert "name" in data
