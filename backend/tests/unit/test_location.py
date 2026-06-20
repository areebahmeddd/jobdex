import pytest

from app.ingestion.normalizer.location import (
    canonicalize_city,
    get_region_for_country,
    is_blocked_location,
    normalize_location,
)


class TestCanonicalizeCity:
    def test_exact_match(self):
        assert canonicalize_city("San Francisco") == "San Francisco"

    def test_case_insensitive(self):
        assert canonicalize_city("san francisco") == "San Francisco"
        assert canonicalize_city("LONDON") == "London"

    @pytest.mark.parametrize(
        "alias, canonical",
        [
            ("nyc", "New York"),
            ("sf", "San Francisco"),
            ("bengaluru", "Bangalore"),
            ("blr", "Bangalore"),
            ("bombay", "Mumbai"),
            ("new delhi", "Delhi"),
            ("dc", "Washington DC"),
        ],
    )
    def test_aliases(self, alias, canonical):
        assert canonicalize_city(alias) == canonical

    def test_unknown_city_returns_none(self):
        assert canonicalize_city("ZZZZZ999QQQQQ") is None

    def test_strips_whitespace(self):
        assert canonicalize_city("  London  ") == "London"

    def test_comma_suffix_alias(self):
        assert canonicalize_city("Bengaluru, KA") == "Bangalore"

    def test_comma_suffix_exact(self):
        assert canonicalize_city("New York, NY") == "New York"

    def test_fuzzy_qualifier_prefix(self):
        assert canonicalize_city("Greater Munich Area") == "Munich"


class TestNormalizeLocation:
    def test_known_city(self):
        r = normalize_location("Bangalore")
        assert r["city"] == "Bangalore"
        assert r["country_code"] == "IN"
        assert r["is_remote"] is False
        assert r["latitude"] is not None

    def test_alias_resolution(self):
        r = normalize_location("NYC")
        assert r["city"] == "New York"

    def test_city_with_suffix(self):
        r = normalize_location("Bangalore, India")
        assert r["city"] == "Bangalore"

    def test_fully_remote(self):
        r = normalize_location("Remote")
        assert r["is_remote"] is True
        assert r["remote_type"] == "fully-remote"
        assert r["city"] is None

    def test_hybrid(self):
        r = normalize_location("Hybrid / London")
        assert r["is_remote"] is True
        assert r["remote_type"] == "hybrid"

    def test_remote_with_known_city(self):
        r = normalize_location("Remote - London")
        assert r["is_remote"] is True
        assert r["city"] == "London"

    def test_fallback_city(self):
        r = normalize_location("", fallback_city="Singapore")
        assert r["city"] == "Singapore"

    def test_fallback_country_code(self):
        r = normalize_location("", fallback_country_code="DE")
        assert r["country_code"] == "DE"

    def test_empty_string(self):
        r = normalize_location("")
        assert r["city"] is None
        assert r["is_remote"] is False

    def test_blocked_location_passthrough(self):
        # normalize_location itself doesn't block; is_blocked_location is called by the caller
        r = normalize_location("Tel Aviv")
        assert r["city"] == "Tel Aviv"


class TestGetRegionForCountry:
    @pytest.mark.parametrize(
        "country_code, expected_region",
        [
            ("US", "north_america"),
            ("CA", "north_america"),
            ("GB", "europe"),
            ("DE", "europe"),
            ("IN", "south_asia"),
            ("AE", "middle_east"),
            ("SG", "asia_pacific"),
            ("AU", "asia_pacific"),
            ("BR", "latin_america"),
            ("NG", "africa"),
        ],
    )
    def test_known_country_codes(self, country_code, expected_region):
        assert get_region_for_country(country_code) == expected_region

    def test_case_insensitive(self):
        assert get_region_for_country("us") == get_region_for_country("US")

    def test_unknown_returns_none(self):
        assert get_region_for_country("ZZ") is None


class TestIsBlockedLocation:
    def test_blocked_country_code(self):
        assert is_blocked_location("IL", None) is True

    def test_blocked_city_tel_aviv(self):
        assert is_blocked_location(None, "Tel Aviv") is True

    def test_blocked_city_case_insensitive(self):
        assert is_blocked_location(None, "tel aviv") is True

    def test_allowed_location(self):
        assert is_blocked_location("US", "San Francisco") is False

    def test_none_both_allowed(self):
        assert is_blocked_location(None, None) is False

    def test_allowed_country_blocked_city_substring(self):
        # City "Israel City" contains "israel"
        assert is_blocked_location("US", "Israel City") is True
