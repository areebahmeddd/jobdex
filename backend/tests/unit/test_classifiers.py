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

    @pytest.mark.parametrize(
        "title, expected_category, expected_subcategory",
        [
            ("Registered Nurse", "healthcare", "clinical"),
            ("Staff Nurse ICU", "healthcare", "clinical"),
            ("Physiotherapist", "healthcare", "clinical"),
            ("Senior Physiotherapist", "healthcare", "clinical"),
            ("Clinical Pharmacist", "healthcare", "clinical"),
            ("Psychiatrist", "healthcare", "clinical"),
            ("Biomedical Engineer", "healthcare", "medtech"),
            ("Clinical Engineer", "healthcare", "medtech"),
            ("Medical Device Specialist", "healthcare", "medtech"),
            ("Regulatory Affairs Manager", "healthcare", "pharma"),
            ("Pharmacovigilance Analyst", "healthcare", "pharma"),
            ("Clinical Trial Manager", "healthcare", "pharma"),
            ("Health Informatics Analyst", "healthcare", "informatics"),
            ("Clinical Informatics Specialist", "healthcare", "informatics"),
        ],
    )
    def test_healthcare_categories(self, title, expected_category, expected_subcategory):
        category, subcategory = classify_role(title)
        assert category == expected_category
        assert subcategory == expected_subcategory

    @pytest.mark.parametrize(
        "title, expected_subcategory",
        [
            ("Head Chef", "culinary"),
            ("Sous Chef", "culinary"),
            ("Pastry Chef", "culinary"),
            ("Line Cook", "culinary"),
            ("Prep Cook", "culinary"),
            ("Baker", "culinary"),
            ("Barista", "culinary"),
            ("Sommelier", "culinary"),
            ("Kitchen Manager", "culinary"),
            ("Bartender", "general"),
            ("Restaurant Manager", "general"),
            ("Hotel Manager", "general"),
            ("Waiter", "general"),
            ("Waitress", "general"),
            ("Concierge", "general"),
            ("Catering Manager", "general"),
            ("Front of House Manager", "general"),
        ],
    )
    def test_hospitality_categories(self, title, expected_subcategory):
        category, subcategory = classify_role(title)
        assert category == "hospitality"
        assert subcategory == expected_subcategory

    def test_fallback_to_other(self):
        category, subcategory = classify_role("Elephant Trainer XYZ123")
        assert category == "other"
        assert subcategory == "general"

    def test_uses_description_as_fallback(self):
        # Title alone is generic; description should disambiguate
        category, _ = classify_role("Associate", description="product management roadmap sprint")
        assert category != "other"


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
