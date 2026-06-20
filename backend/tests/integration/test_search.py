import pytest


@pytest.mark.integration
def test_search_returns_200(client):
    r = client.get("/search")
    assert r.status_code == 200


@pytest.mark.integration
def test_search_schema(client):
    data = client.get("/search").json()
    assert "companies" in data
    assert "jobs" in data
    assert "total_companies" in data
    assert "total_jobs" in data
    assert isinstance(data["companies"], list)
    assert isinstance(data["jobs"], list)


@pytest.mark.integration
def test_search_role_filter(client):
    data = client.get("/search", params={"role": "engineering"}).json()
    for job in data["jobs"]:
        assert job["role_category"] == "engineering"


@pytest.mark.integration
def test_search_city_filter(client):
    data = client.get("/search", params={"city": "Bangalore"}).json()
    for job in data["jobs"]:
        assert job["city"] == "Bangalore"


@pytest.mark.integration
def test_search_totals_consistent(client):
    data = client.get("/search", params={"limit": 5}).json()
    assert data["total_jobs"] >= len(data["jobs"])
    assert data["total_companies"] >= len(data["companies"])


@pytest.mark.integration
def test_search_remote_filter(client):
    data = client.get("/search", params={"is_remote": "true"}).json()
    for job in data["jobs"]:
        assert job["is_remote"] is True
