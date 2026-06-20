import pytest


@pytest.mark.integration
def test_list_cities_returns_200(client):
    r = client.get("/cities")
    assert r.status_code == 200


@pytest.mark.integration
def test_list_cities_schema(client):
    data = client.get("/cities").json()
    assert "cities" in data
    assert "total" in data
    assert isinstance(data["cities"], list)


@pytest.mark.integration
def test_list_cities_has_required_fields(client):
    cities = client.get("/cities").json()["cities"]
    if not cities:
        pytest.skip("No cities in database")
    city = cities[0]
    assert "name" in city
    assert "slug" in city
    assert "country_code" in city


@pytest.mark.integration
def test_list_cities_featured_filter(client):
    data = client.get("/cities", params={"featured_only": "true"}).json()
    for city in data["cities"]:
        assert city["is_featured"] is True


@pytest.mark.integration
def test_list_cities_cache_header(client):
    r = client.get("/cities")
    cc = r.headers.get("cache-control", "")
    assert "max-age=300" in cc


@pytest.mark.integration
def test_get_city_not_found(client):
    r = client.get("/cities/nonexistent-city-xyz")
    assert r.status_code == 404


@pytest.mark.integration
def test_get_city_valid(client):
    cities = client.get("/cities", params={"limit": 1}).json()["cities"]
    if not cities:
        pytest.skip("No cities in database")
    slug = cities[0]["slug"]
    r = client.get(f"/cities/{slug}")
    assert r.status_code == 200
    data = r.json()
    assert data["slug"] == slug


@pytest.mark.integration
def test_get_city_cache_header(client):
    cities = client.get("/cities", params={"limit": 1}).json()["cities"]
    if not cities:
        pytest.skip("No cities in database")
    r = client.get(f"/cities/{cities[0]['slug']}")
    cc = r.headers.get("cache-control", "")
    assert "max-age=300" in cc
