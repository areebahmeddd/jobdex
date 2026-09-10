import pytest


@pytest.mark.integration
def test_list_jobs_schema(client):
    r = client.get("/jobs")
    assert r.status_code == 200
    data = r.json()
    assert "jobs" in data
    assert isinstance(data["total"], int)
    assert "limit" in data
    assert isinstance(data["jobs"], list)


@pytest.mark.integration
def test_list_jobs_respects_limit(client):
    data = client.get("/jobs", params={"limit": 5}).json()
    assert len(data["jobs"]) <= 5


@pytest.mark.integration
def test_list_jobs_role_filter(client):
    data = client.get("/jobs", params={"role_category": "engineering", "limit": 20}).json()
    assert len(data["jobs"]) > 0
    for job in data["jobs"]:
        assert job["role_category"] == "engineering"


@pytest.mark.integration
def test_list_jobs_seniority_filter(client):
    data = client.get("/jobs", params={"seniority": "senior", "limit": 10}).json()
    assert len(data["jobs"]) > 0
    for job in data["jobs"]:
        assert job["seniority"] == "senior"


@pytest.mark.integration
def test_list_jobs_remote_filter(client):
    data = client.get("/jobs", params={"is_remote": "true", "limit": 20}).json()
    assert len(data["jobs"]) > 0
    for job in data["jobs"]:
        assert job["is_remote"] is True


@pytest.mark.integration
def test_list_jobs_fulltext_search(client):
    r = client.get("/jobs", params={"q": "engineer", "limit": 5})
    assert r.status_code == 200
    assert "jobs" in r.json()


@pytest.mark.integration
def test_list_jobs_cursor_pagination(client):
    page1 = client.get("/jobs", params={"limit": 5}).json()
    cursor = page1.get("next_cursor")
    if cursor:
        page2 = client.get("/jobs", params={"limit": 5, "cursor": cursor}).json()
        assert "jobs" in page2
        ids1 = {j["id"] for j in page1["jobs"]}
        ids2 = {j["id"] for j in page2["jobs"]}
        assert ids1.isdisjoint(ids2)


@pytest.mark.integration
def test_list_jobs_invalid_cursor_graceful(client):
    r = client.get("/jobs", params={"cursor": "this-is-not-a-valid-cursor"})
    assert r.status_code == 200


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
def test_list_jobs_multi_source_filter(client):
    data = client.get(
        "/jobs", params=[("ats_type", "lever"), ("ats_type", "ashby"), ("limit", 20)]
    ).json()
    for job in data["jobs"]:
        assert job["ats_type"] in {"lever", "ashby"}


@pytest.mark.integration
def test_list_jobs_source_filter_narrows_total(client):
    everything = client.get("/jobs", params={"limit": 1}).json()["total"]
    one_source = client.get("/jobs", params={"ats_type": "lever", "limit": 1}).json()["total"]
    assert 0 <= one_source <= everything


@pytest.mark.integration
def test_list_jobs_work_mode_onsite(client):
    data = client.get("/jobs", params={"work_mode": "onsite", "limit": 20}).json()
    for job in data["jobs"]:
        assert job["is_remote"] is False


@pytest.mark.integration
def test_list_jobs_work_mode_hybrid(client):
    data = client.get("/jobs", params={"work_mode": "hybrid", "limit": 20}).json()
    for job in data["jobs"]:
        assert job["is_remote"] is True
        assert job["remote_type"] == "hybrid"


@pytest.mark.integration
def test_list_jobs_multi_seniority_filter(client):
    data = client.get(
        "/jobs", params=[("seniority", "senior"), ("seniority", "staff"), ("limit", 20)]
    ).json()
    for job in data["jobs"]:
        assert job["seniority"] in {"senior", "staff"}


@pytest.mark.integration
def test_list_jobs_posted_within_rejects_out_of_range(client):
    assert client.get("/jobs", params={"posted_within": 0}).status_code == 422
    assert client.get("/jobs", params={"posted_within": 999}).status_code == 422


@pytest.mark.integration
def test_list_jobs_relevance_sort_uses_offset_pagination(client):
    data = client.get("/jobs", params={"q": "engineer", "sort": "relevance", "limit": 5}).json()
    assert data["sort"] == "relevance"
    assert data["next_cursor"] is None
    assert isinstance(data["total"], int)


@pytest.mark.integration
def test_list_jobs_unknown_sort_falls_back_to_recent(client):
    data = client.get("/jobs", params={"q": "engineer", "sort": "nonsense", "limit": 5}).json()
    assert data["sort"] == "recent"


@pytest.mark.integration
def test_list_jobs_cursor_reaches_jobs_without_a_posted_date(client):
    """Undated jobs sort last, so they are only reachable if the cursor admits NULLs."""
    seen, cursor = [], None
    for _ in range(15):
        params = {"city": "Gurgaon", "limit": 10}
        if cursor:
            params["cursor"] = cursor
        page = client.get("/jobs", params=params).json()
        seen.extend(page["jobs"])
        cursor = page.get("next_cursor")
        if not cursor or not page["jobs"]:
            break

    total = client.get("/jobs", params={"city": "Gurgaon", "limit": 1}).json()["total"]
    if total == 0:
        pytest.skip("No jobs in this city")
    ids = [j["id"] for j in seen]
    assert len(ids) == len(set(ids))
    assert len(ids) == total


@pytest.mark.integration
def test_job_facets_schema(client):
    data = client.get("/jobs/facets").json()
    assert isinstance(data["total"], int)
    for dimension in ("ats_type", "role_category", "seniority", "job_type", "work_mode"):
        assert isinstance(data[dimension], list)
        for bucket in data[dimension]:
            assert bucket["count"] > 0
            assert bucket["value"]


@pytest.mark.integration
def test_job_facet_counts_match_the_list_total(client):
    facets = client.get("/jobs/facets", params={"work_mode": "hybrid"}).json()
    listed = client.get("/jobs", params={"work_mode": "hybrid", "limit": 1}).json()
    assert facets["total"] == listed["total"]


@pytest.mark.integration
def test_job_facets_ignore_their_own_dimension(client):
    """Picking one source must still show what the other sources would return."""
    facets = client.get("/jobs/facets", params={"ats_type": "lever"}).json()
    sources = {b["value"] for b in facets["ats_type"]}
    assert len(sources) > 1


@pytest.mark.integration
def test_job_facets_respect_other_dimensions(client):
    unfiltered = client.get("/jobs/facets").json()
    scoped = client.get("/jobs/facets", params={"work_mode": "hybrid"}).json()
    by_source = {b["value"]: b["count"] for b in unfiltered["ats_type"]}
    for bucket in scoped["ats_type"]:
        assert bucket["count"] <= by_source.get(bucket["value"], 0)
