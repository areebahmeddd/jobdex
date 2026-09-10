import pytest


@pytest.mark.integration
def test_list_companies_schema(client):
    r = client.get("/companies", params={"limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert "companies" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["companies"], list)
    if data["companies"]:
        c = data["companies"][0]
        assert "id" in c
        assert "name" in c
        assert "slug" in c
        assert "job_count" in c


@pytest.mark.integration
def test_list_companies_respects_limit(client):
    data = client.get("/companies", params={"limit": 3}).json()
    assert len(data["companies"]) <= 3


@pytest.mark.integration
def test_list_companies_has_errors_filter(client):
    r = client.get("/companies", params={"has_errors": "false"})
    assert r.status_code == 200
    assert "companies" in r.json()


@pytest.mark.integration
def test_list_companies_text_search(client):
    r = client.get("/companies", params={"q": "tech", "limit": 5})
    assert r.status_code == 200
    assert "companies" in r.json()


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


@pytest.mark.integration
def test_list_companies_role_filter_narrows_and_rescopes_counts(client):
    """A role filter must be applied in SQL, and job_count must reflect it."""
    city = "Bangalore"
    unscoped = client.get("/companies", params={"city": city, "limit": 100}).json()
    if unscoped["total"] == 0:
        pytest.skip("No companies in this city")
    scoped = client.get(
        "/companies", params={"city": city, "role_category": "design", "limit": 100}
    ).json()

    assert scoped["total"] <= unscoped["total"]
    by_slug = {c["slug"]: c["job_count"] for c in unscoped["companies"]}
    for company in scoped["companies"]:
        assert company["job_count"] > 0
        assert company["job_count"] <= by_slug.get(company["slug"], company["job_count"])


@pytest.mark.integration
def test_list_companies_unfiltered_keeps_companies_without_open_roles(client):
    everything = client.get("/companies", params={"limit": 1}).json()["total"]
    hiring = client.get("/companies", params={"role_category": "engineering", "limit": 1}).json()
    assert hiring["total"] <= everything


@pytest.mark.integration
def test_company_jobs_accept_the_shared_filter_set(client):
    companies = client.get(
        "/companies", params={"role_category": "engineering", "limit": 1}
    ).json()["companies"]
    if not companies:
        pytest.skip("No hiring companies in database")
    slug = companies[0]["slug"]
    data = client.get(
        f"/companies/{slug}/jobs", params={"role_category": "engineering", "limit": 20}
    ).json()
    for job in data["jobs"]:
        assert job["role_category"] == "engineering"
