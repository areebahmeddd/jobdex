import pytest


@pytest.mark.integration
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.integration
def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "name" in data
    assert "supported_ats" in data
    assert "ashby" in data["supported_ats"]
    assert "endpoints" in data
