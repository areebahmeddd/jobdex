import pytest


@pytest.mark.integration
def test_stats_returns_200(client):
    r = client.get("/stats")
    assert r.status_code == 200


@pytest.mark.integration
def test_stats_schema(client):
    data = client.get("/stats").json()
    assert isinstance(data["total_companies"], int)
    assert isinstance(data["total_jobs"], int)
    assert isinstance(data["active_jobs"], int)
    assert isinstance(data["total_cities"], int)
    assert isinstance(data["role_categories"], dict)
    assert isinstance(data["top_cities"], list)
    assert isinstance(data["top_regions"], list)
    assert isinstance(data["ats_breakdown"], dict)


@pytest.mark.integration
def test_stats_active_lte_total(client):
    data = client.get("/stats").json()
    assert data["active_jobs"] <= data["total_jobs"]


@pytest.mark.integration
def test_stats_cities_with_jobs_lte_total_cities(client):
    data = client.get("/stats").json()
    assert data["cities_with_jobs"] <= data["total_cities"]


@pytest.mark.integration
def test_stats_cache_header(client):
    r = client.get("/stats")
    cc = r.headers.get("cache-control", "")
    assert "max-age=300" in cc
