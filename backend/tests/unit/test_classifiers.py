import pytest

from app.ingestion.normalizer.classifiers import (
    classify_role,
    classify_seniority,
    extract_tech_stack,
    normalize_job_type,
)


class TestClassifySeniority:
    @pytest.mark.parametrize(
        "title, expected",
        [
            ("Software Engineering Intern", "intern"),
            ("Junior Frontend Developer", "junior"),
            ("Senior Software Engineer", "senior"),
            ("Staff Engineer", "staff"),
            ("Lead Engineer", "lead"),
            ("Tech Lead", "lead"),
            ("Engineering Manager", "manager"),
            ("Director of Engineering", "director"),
            ("Head of Product", "director"),
            ("VP of Engineering", "executive"),
            ("Chief Technology Officer", "executive"),
            ("Principal Engineer", "principal"),
        ],
    )
    def test_seniority_levels(self, title, expected):
        assert classify_seniority(title) == expected

    def test_defaults_to_mid(self):
        assert classify_seniority("Software Engineer") == "mid"
        assert classify_seniority("Backend Developer") == "mid"

    def test_case_insensitive(self):
        assert classify_seniority("SENIOR ENGINEER") == classify_seniority("senior engineer")


class TestClassifyRole:
    @pytest.mark.parametrize(
        "title, expected_category",
        [
            ("Software Engineer", "engineering"),
            ("Backend Developer", "engineering"),
            ("Frontend Engineer", "engineering"),
            ("Product Manager", "product"),
            ("UX Designer", "design"),
            ("Product Designer", "design"),
            ("Sales Development Representative", "sales"),
            ("Marketing Manager", "marketing"),
            ("Account Executive", "sales"),
        ],
    )
    def test_role_categories(self, title, expected_category):
        category, _ = classify_role(title)
        assert category == expected_category

    def test_returns_tuple_of_two(self):
        result = classify_role("Backend Engineer")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_fallback_to_other(self):
        category, subcategory = classify_role("Elephant Trainer XYZ123")
        assert category == "other"
        assert subcategory == "general"

    def test_uses_description_as_fallback(self):
        # Title alone is generic; description should disambiguate
        category, _ = classify_role("Associate", description="product management roadmap sprint")
        assert category != "other"

    def test_subcategory_is_string(self):
        _, subcategory = classify_role("Data Scientist")
        assert isinstance(subcategory, str)


class TestExtractTechStack:
    def test_finds_python(self):
        result = extract_tech_stack("Python Developer", "experience with Python and Django")
        assert "python" in result

    def test_returns_sorted_list(self):
        result = extract_tech_stack("", "python javascript react aws")
        assert result == sorted(result)

    def test_empty_inputs_return_empty(self):
        assert extract_tech_stack("", "") == []

    def test_no_partial_word_match(self):
        # "go" should not match inside other words
        result = extract_tech_stack("django developer", "")
        assert "go" not in result

    def test_finds_multiple_keywords(self):
        result = extract_tech_stack("", "react typescript postgresql redis docker")
        assert len(result) >= 3

    def test_case_insensitive(self):
        lower = extract_tech_stack("python", "")
        upper = extract_tech_stack("PYTHON", "")
        assert lower == upper


class TestNormalizeJobType:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("full-time", "fulltime"),
            ("Full-Time", "fulltime"),
            ("FULL_TIME", None),  # not in map
            ("part-time", "parttime"),
            ("contract", "contract"),
            ("freelance", "contract"),
            ("internship", "internship"),
        ],
    )
    def test_known_mappings(self, raw, expected):
        assert normalize_job_type(raw) == expected

    def test_empty_string_returns_none(self):
        assert normalize_job_type("") is None

    def test_unknown_returns_none(self):
        assert normalize_job_type("INVALID_TYPE_XYZ") is None
