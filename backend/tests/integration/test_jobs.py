import pytest


@pytest.mark.integration
def test_list_jobs_returns_200(client):
    r = client.get("/jobs")
    assert r.status_code == 200


@pytest.mark.integration
def test_list_jobs_schema(client):
    data = client.get("/jobs").json()
    assert "jobs" in data
    assert "total" in data
    assert "limit" in data
    assert isinstance(data["jobs"], list)


@pytest.mark.integration
def test_list_jobs_respects_limit(client):
    data = client.get("/jobs", params={"limit": 5}).json()
    assert len(data["jobs"]) <= 5


@pytest.mark.integration
def test_list_jobs_role_filter(client):
    data = client.get("/jobs", params={"role_category": "engineering", "limit": 20}).json()
    for job in data["jobs"]:
        assert job["role_category"] == "engineering"


@pytest.mark.integration
def test_list_jobs_remote_filter(client):
    data = client.get("/jobs", params={"is_remote": "true", "limit": 20}).json()
    for job in data["jobs"]:
        assert job["is_remote"] is True


@pytest.mark.integration
def test_list_jobs_cursor_pagination(client):
    page1 = client.get("/jobs", params={"limit": 5}).json()
    cursor = page1.get("next_cursor")
    if cursor:
        page2 = client.get("/jobs", params={"limit": 5, "cursor": cursor}).json()
        assert "jobs" in page2
        # No overlap between pages
        ids1 = {j["id"] for j in page1["jobs"]}
        ids2 = {j["id"] for j in page2["jobs"]}
        assert ids1.isdisjoint(ids2)


@pytest.mark.integration
def test_get_job_not_found(client):
    r = client.get("/jobs/nonexistent-id-xyz")
    assert r.status_code == 404


@pytest.mark.integration
def test_get_job_valid(client):
    jobs = client.get("/jobs", params={"limit": 1}).json()["jobs"]
    if not jobs:
        pytest.skip("No jobs in database")
    job_id = jobs[0]["id"]
    r = client.get(f"/jobs/{job_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == job_id
    assert "title" in data
    assert "company_name" in data


@pytest.mark.integration
def test_get_job_cache_header(client):
    jobs = client.get("/jobs", params={"limit": 1}).json()["jobs"]
    if not jobs:
        pytest.skip("No jobs in database")
    r = client.get(f"/jobs/{jobs[0]['id']}")
    cc = r.headers.get("cache-control", "")
    assert "max-age=60" in cc
