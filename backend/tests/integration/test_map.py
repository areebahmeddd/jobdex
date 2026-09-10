import pytest


@pytest.mark.integration
def test_map_companies_schema(client):
    r = client.get("/map/companies")
    assert r.status_code == 200
    data = r.json()
    assert "companies" in data
    assert "total" in data
    assert isinstance(data["companies"], list)


@pytest.mark.integration
def test_map_companies_pin_fields(client):
    companies = client.get("/map/companies").json()["companies"]
    if not companies:
        pytest.skip("No companies with coordinates in database")
    pin = companies[0]
    assert "id" in pin
    assert "name" in pin
    assert "slug" in pin
    assert "latitude" in pin
    assert "longitude" in pin
    assert -90 <= pin["latitude"] <= 90
    assert -180 <= pin["longitude"] <= 180


@pytest.mark.integration
def test_map_companies_cache_header(client):
    r = client.get("/map/companies")
    cc = r.headers.get("cache-control", "")
    assert "max-age=120" in cc


@pytest.mark.integration
def test_map_companies_viewport_filter(client):
    r = client.get(
        "/map/companies",
        params={"lat_min": 8.0, "lat_max": 37.0, "lng_min": 68.0, "lng_max": 97.0},
    )
    assert r.status_code == 200
    assert "companies" in r.json()


@pytest.mark.integration
def test_map_companies_invalid_viewport_returns_422(client):
    r = client.get("/map/companies", params={"lat_min": 91})
    assert r.status_code == 422


@pytest.mark.integration
def test_map_cities_schema(client):
    r = client.get("/map/cities")
    assert r.status_code == 200
    data = r.json()
    assert "cities" in data
    assert "total" in data


@pytest.mark.integration
def test_map_cities_cache_header(client):
    r = client.get("/map/cities")
    cc = r.headers.get("cache-control", "")
    assert "max-age=120" in cc


@pytest.mark.integration
def test_map_company_offices_valid(client):
    companies = client.get("/companies", params={"limit": 1}).json()["companies"]
    if not companies:
        pytest.skip("No companies in database")
    slug = companies[0]["slug"]
    r = client.get(f"/map/companies/{slug}/offices")
    assert r.status_code == 200
    data = r.json()
    assert "offices" in data
    assert isinstance(data["offices"], list)


@pytest.mark.integration
def test_map_company_offices_not_found(client):
    r = client.get("/map/companies/nonexistent-xyz/offices")
    assert r.status_code == 404


@pytest.mark.integration
def test_map_cities_respects_the_search_term(client):
    """The map is a result surface, so a search term must narrow the pins too."""
    everything = client.get("/map/cities").json()["total"]
    searched = client.get("/map/cities", params={"q": "rust"}).json()
    assert searched["total"] <= everything
    for city in searched["cities"]:
        assert city["job_count"] > 0


@pytest.mark.integration
def test_map_companies_respects_the_source_filter(client):
    data = client.get("/map/companies", params={"ats_type": "lever"}).json()
    for pin in data["companies"]:
        assert pin["job_count"] > 0


@pytest.mark.integration
def test_map_companies_role_filter_narrows_counts(client):
    everything = client.get("/map/companies").json()
    scoped = client.get("/map/companies", params={"role_category": "design"}).json()
    baseline = {p["slug"]: p["job_count"] for p in everything["companies"]}
    for pin in scoped["companies"]:
        if pin["slug"] in baseline:
            assert pin["job_count"] <= baseline[pin["slug"]]
