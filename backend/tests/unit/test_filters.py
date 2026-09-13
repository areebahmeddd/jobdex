from app.routers._filters import (
    WORK_MODES,
    JobFilters,
    _clean_multi,
)


class TestMultiValueCleaning:
    def test_lowercases_and_dedupes(self):
        assert _clean_multi(["Engineering", "engineering", "DESIGN"]) == ["engineering", "design"]

    def test_drops_blanks(self):
        assert _clean_multi(["  ", "", "lever"]) == ["lever"]

    def test_caps_value_count(self):
        assert len(_clean_multi([f"v{i}" for i in range(200)])) == 25

    def test_caps_value_length(self):
        assert len(_clean_multi(["x" * 500])[0]) == 100

    def test_none_is_empty(self):
        assert _clean_multi(None) == []


class TestJobFilters:
    def test_normalizes_scalars(self):
        f = JobFilters(country_code=" in ", region=" South_Asia ", q="  rust  ")
        assert f.country_code == "IN"
        assert f.region == "south_asia"
        assert f.q == "rust"

    def test_blank_query_is_none(self):
        assert JobFilters(q="   ").q is None

    def test_query_length_is_capped(self):
        assert len(JobFilters(q="a" * 5000).q) == 200

    def test_unknown_work_modes_are_dropped(self):
        f = JobFilters(work_mode=["remote", "telepathic", "onsite"])
        assert f.work_mode == ["remote", "onsite"]
        assert all(m in WORK_MODES for m in f.work_mode)

    def test_without_clears_named_dimensions_only(self):
        f = JobFilters(city="Berlin", region="europe", ats_type=["lever"], seniority=["senior"])
        stripped = f.without("city", "region", "ats_type")
        assert stripped.city is None
        assert stripped.region is None
        assert stripped.ats_type == []
        assert stripped.seniority == ["senior"]

    def test_without_does_not_mutate_the_original(self):
        f = JobFilters(city="Berlin", ats_type=["lever"])
        f.without("city", "ats_type")
        assert f.city == "Berlin"
        assert f.ats_type == ["lever"]
