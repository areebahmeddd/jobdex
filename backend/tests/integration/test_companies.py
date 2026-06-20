import pytest


@pytest.mark.integration
def test_list_companies_returns_200(client):
    r = client.get("/companies")
    assert r.status_code == 200


@pytest.mark.integration
def test_list_companies_schema(client):
    data = client.get("/companies").json()
    assert "companies" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["companies"], list)


@pytest.mark.integration
def test_list_companies_has_required_fields(client):
    companies = client.get("/companies", params={"limit": 5}).json()["companies"]
    if not companies:
        pytest.skip("No companies in database")
    c = companies[0]
    assert "id" in c
    assert "name" in c
    assert "slug" in c
    assert "job_count" in c


@pytest.mark.integration
def test_list_companies_respects_limit(client):
    data = client.get("/companies", params={"limit": 3}).json()
    assert len(data["companies"]) <= 3


@pytest.mark.integration
def test_get_company_not_found(client):
    r = client.get("/companies/nonexistent-slug-xyz")
    assert r.status_code == 404


@pytest.mark.integration
def test_get_company_valid(client):
    companies = client.get("/companies", params={"limit": 1}).json()["companies"]
    if not companies:
        pytest.skip("No companies in database")
    slug = companies[0]["slug"]
    r = client.get(f"/companies/{slug}")
    assert r.status_code == 200
    data = r.json()
    assert data["slug"] == slug
    assert "name" in data
    assert "job_count" in data


@pytest.mark.integration
def test_list_company_jobs(client):
    companies = client.get("/companies", params={"limit": 1}).json()["companies"]
    if not companies:
        pytest.skip("No companies in database")
    slug = companies[0]["slug"]
    r = client.get(f"/companies/{slug}/jobs")
    assert r.status_code == 200
    data = r.json()
    assert "jobs" in data
    assert "total" in data
