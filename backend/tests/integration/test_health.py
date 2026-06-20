import pytest


@pytest.mark.integration
def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200


@pytest.mark.integration
def test_health_status_ok(client):
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.integration
def test_root_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200


@pytest.mark.integration
def test_root_has_name(client):
    data = client.get("/").json()
    assert "name" in data
