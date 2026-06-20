import pytest

from app.ingestion.normalizer.location import (
    canonicalize_city,
    get_region_for_country,
    is_blocked_location,
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
        assert canonicalize_city("Nonexistent City XYZXYZ") is None

    def test_strips_whitespace(self):
        assert canonicalize_city("  London  ") == "London"


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
