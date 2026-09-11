import pytest

from app.ingestion.normalizer.location import (
    canonicalize_city,
    get_country_code_for_name,
    get_region_for_country,
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


class TestGetCountryCodeForName:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("United States", "US"),
            ("Germany", "DE"),
            ("India", "IN"),
            ("Singapore", "SG"),
        ],
    )
    def test_names_from_city_table(self, name, expected):
        assert get_country_code_for_name(name) == expected

    @pytest.mark.parametrize(
        "name, expected",
        [
            ("United States of America", "US"),
            ("USA", "US"),
            ("England", "GB"),
            ("United Kingdom of Great Britain and Northern Ireland", "GB"),
            ("Czechia", "CZ"),
            ("Republic of Korea", "KR"),
            ("Viet Nam", "VN"),
        ],
    )
    def test_long_form_aliases(self, name, expected):
        assert get_country_code_for_name(name) == expected

    def test_case_and_whitespace_insensitive(self):
        assert get_country_code_for_name("  uNiTeD sTaTeS  ") == "US"

    @pytest.mark.parametrize("name", [None, "", "   ", "Atlantis"])
    def test_unknown_returns_none(self, name):
        assert get_country_code_for_name(name) is None


class TestCountryPrefixedLocations:
    """Boards commonly prefix the place with a country or region."""

    @pytest.mark.parametrize(
        "raw,city,country_code",
        [
            ("IN - Bengaluru, India", "Bangalore", "IN"),
            ("Brazil - Sao Paulo", "São Paulo", "BR"),
            ("Malaysia - Petaling Jaya", "Kuala Lumpur", "MY"),
            ("US - Washington, DC", "Washington DC", "US"),
            ("Batu Kawan, Pulau Pinang (Penang), Malaysia", "Penang", "MY"),
        ],
    )
    def test_segment_resolves_the_city(self, raw, city, country_code):
        result = normalize_location(raw)
        assert result["city"] == city
        assert result["country_code"] == country_code

    def test_segments_match_exactly_not_as_substrings(self):
        """A short alias must not match inside an unrelated word."""
        assert normalize_location("Transfer Station")["city"] is None


class TestHeadquartersFallback:
    """The company HQ fills unresolved fields, but must not override another country."""

    def test_bare_remote_inherits_the_headquarters(self):
        result = normalize_location(
            "Remote", fallback_city="San Francisco", fallback_country_code="US"
        )
        assert result["city"] == "San Francisco"
        assert result["is_remote"] is True

    def test_same_country_inherits_the_headquarters(self):
        result = normalize_location(
            "Remote - US", fallback_city="Austin", fallback_country_code="US"
        )
        assert result["city"] == "Austin"

    @pytest.mark.parametrize(
        "raw,country_code",
        [
            ("India", "IN"),
            ("Philippines", "PH"),
            ("Bogota, Colombia", "CO"),
            ("BR - Remote - Brazil", "BR"),
        ],
    )
    def test_another_country_wins_over_the_headquarters(self, raw, country_code):
        result = normalize_location(raw, fallback_city="Austin", fallback_country_code="US")
        assert result["city"] is None
        assert result["country_code"] == country_code

    def test_no_headquarters_leaves_the_city_empty(self):
        assert normalize_location("Somewhere Unknown")["city"] is None
