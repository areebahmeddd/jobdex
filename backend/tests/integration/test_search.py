import pytest


@pytest.mark.integration
def test_search_schema(client):
    r = client.get("/search")
    assert r.status_code == 200
    data = r.json()
    assert "companies" in data
    assert "jobs" in data
    assert "total_companies" in data
    assert "total_jobs" in data
    assert isinstance(data["companies"], list)
    assert isinstance(data["jobs"], list)


@pytest.mark.integration
def test_search_role_filter(client):
    data = client.get("/search", params={"role": "engineering"}).json()
    assert len(data["jobs"]) > 0
    for job in data["jobs"]:
        assert job["role_category"] == "engineering"


@pytest.mark.integration
def test_search_city_filter(client):
    data = client.get("/search", params={"city": "Bangalore"}).json()
    assert len(data["jobs"]) > 0
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
    assert len(data["jobs"]) > 0
    for job in data["jobs"]:
        assert job["is_remote"] is True


@pytest.mark.integration
def test_search_country_code_filter(client):
    data = client.get("/search", params={"country_code": "IN", "limit": 10}).json()
    assert len(data["jobs"]) > 0
    for job in data["jobs"]:
        assert job["country_code"] == "IN"


@pytest.mark.integration
def test_search_accepts_a_text_query(client):
    r = client.get("/search", params={"q": "engineer", "limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["total_jobs"] <= client.get("/search", params={"limit": 1}).json()["total_jobs"]


@pytest.mark.integration
def test_search_accepts_multi_value_filters(client):
    data = client.get(
        "/search",
        params=[("role_category", "engineering"), ("role_category", "design"), ("limit", 20)],
    ).json()
    for job in data["jobs"]:
        assert job["role_category"] in {"engineering", "design"}


@pytest.mark.integration
def test_search_role_alias_matches_role_category(client):
    alias = client.get("/search", params={"role": "design", "limit": 1}).json()
    explicit = client.get("/search", params={"role_category": "design", "limit": 1}).json()
    assert alias["total_jobs"] == explicit["total_jobs"]
