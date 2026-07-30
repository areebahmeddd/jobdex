"""Unit tests for the ATS ingesters that parse without touching the network or DB.

build_job() only needs an unsaved Company, so each test drives a real ATS payload
shape through the ingester and asserts on the normalized Job fields.
"""

import json

import pytest

from app.config import DATA_DIR
from app.ingestion import INGESTERS, rippling, teamtailor, workday
from app.ingestion.workday import _parse_slug
from app.models import Company


@pytest.fixture
def company():
    return Company(
        id="00000000-0000-0000-0000-000000000000",
        name="Acme",
        slug="acme",
        ats_type="test",
        ats_slug="acme",
    )


TEAMTAILOR_ITEM = {
    "id": "eb979d2f-98d0-45f5-a647-3b05cac782c2",
    "title": "Staff Engineer, Consumer domain",
    "url": "https://instabee.teamtailor.com/jobs/7763789-staff-engineer",
    "date_published": "2026-05-20T10:07:53+02:00",
    "content_html": "<p>We build <strong>delivery</strong> software in Python and Kubernetes.</p>",
    "_jobposting": {
        "@type": "JobPosting",
        "title": "Staff Engineer, Consumer domain",
        "identifier": {"@type": "PropertyValue", "name": "Instabee", "value": 7763789},
        "datePosted": "2026-05-20T10:07:53+02:00",
        "hiringOrganization": {
            "@type": "Organization",
            "name": "Instabee",
            "sameAs": "https://career.instabee.com",
        },
        "jobLocation": [
            {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "Halsingegatan 40",
                    "addressLocality": "Stockholm",
                    "postalCode": "113 43",
                    "addressCountry": "SE",
                    "addressRegion": "Sweden",
                },
            }
        ],
    },
}


class TestTeamtailor:
    def test_job_id_prefers_schema_identifier(self):
        assert teamtailor.extract_job_id(TEAMTAILOR_ITEM) == "7763789"

    def test_job_id_falls_back_to_feed_uuid(self):
        item = {**TEAMTAILOR_ITEM, "_jobposting": {}}
        assert teamtailor.extract_job_id(item) == TEAMTAILOR_ITEM["id"]

    def test_build_job_resolves_location(self, company):
        job = teamtailor.build_job(TEAMTAILOR_ITEM, company, "instabee")
        assert job.city == "Stockholm"
        assert job.country_code == "SE"
        assert job.region == "europe"
        assert job.latitude is not None

    def test_build_job_classifies_and_strips_html(self, company):
        job = teamtailor.build_job(TEAMTAILOR_ITEM, company, "instabee")
        assert job.title == "Staff Engineer, Consumer domain"
        assert job.role_category == "engineering"
        assert job.seniority == "staff"
        assert "<strong>" not in job.description
        assert "python" in job.tech_stack

    def test_build_job_sets_posted_at_and_source(self, company):
        job = teamtailor.build_job(TEAMTAILOR_ITEM, company, "instabee")
        assert job.posted_at is not None
        assert job.posted_at.year == 2026
        assert job.source_url == TEAMTAILOR_ITEM["url"]
        assert job.ats_type == "teamtailor"

    def test_build_job_backfills_company_website(self, company):
        teamtailor.build_job(TEAMTAILOR_ITEM, company, "instabee")
        assert company.website == "https://career.instabee.com"

    def test_missing_location_is_treated_as_remote(self, company):
        item = {
            **TEAMTAILOR_ITEM,
            "_jobposting": {**TEAMTAILOR_ITEM["_jobposting"], "jobLocation": []},
        }
        job = teamtailor.build_job(item, company, "instabee")
        assert job.location_raw == "Remote"
        assert job.is_remote is True

    def test_intern_title_sets_job_type(self, company):
        item = {**TEAMTAILOR_ITEM, "title": "Backend Engineering Intern"}
        job = teamtailor.build_job(item, company, "instabee")
        assert job.seniority == "intern"
        assert job.job_type == "intern"


WORKDAY_JOB = {
    "title": "Senior Machine Learning Engineer",
    "externalPath": "/job/US-CA-Santa-Clara/Senior-ML-Engineer_JR2020107",
    "locationsText": "US, CA, Santa Clara",
    "postedOn": "Posted Today",
    "bulletFields": ["JR2020107"],
    # merged in from the per-job detail fetch
    "jobDescription": "<p>Build training pipelines with PyTorch and CUDA.</p>",
    "location": "San Diego",
    "startDate": "2026-07-30",
    "timeType": "Full time",
    "country": {"descriptor": "United States of America"},
    "externalUrl": "https://nvidia.wd5.myworkdayjobs.com/Site/job/Senior-ML-Engineer_JR2020107",
}


class TestWorkdaySlug:
    def test_parses_composite_slug(self):
        assert _parse_slug("nvidia:wd5:NVIDIAExternalCareerSite") == (
            "nvidia",
            "wd5",
            "NVIDIAExternalCareerSite",
        )

    def test_strips_whitespace(self):
        assert _parse_slug(" nvidia : wd5 : Site ") == ("nvidia", "wd5", "Site")

    def test_bare_tenant_gets_defaults(self):
        assert _parse_slug("acme") == ("acme", "wd1", "External")

    @pytest.mark.parametrize("bad", ["", "a:b", "a::c", ":wd1:board", "a:b:c:d"])
    def test_rejects_malformed_slug(self, bad):
        with pytest.raises(ValueError):
            _parse_slug(bad)


class TestWorkday:
    def test_job_id_uses_requisition_number(self):
        assert workday.extract_job_id(WORKDAY_JOB) == "JR2020107"

    def test_job_id_falls_back_to_external_path(self):
        job = {**WORKDAY_JOB, "bulletFields": []}
        assert workday.extract_job_id(job) == WORKDAY_JOB["externalPath"]

    def test_build_job_prefers_detail_location(self, company):
        job = workday.build_job(WORKDAY_JOB, company, "nvidia:wd5:Site")
        assert job.location_raw == "San Diego"
        assert job.city == "San Diego"
        assert job.country_code == "US"
        assert job.region == "north_america"

    def test_build_job_classifies(self, company):
        job = workday.build_job(WORKDAY_JOB, company, "nvidia:wd5:Site")
        assert job.role_category == "engineering"
        assert job.seniority == "senior"
        assert job.job_type == "fulltime"
        assert "pytorch" in job.tech_stack

    def test_posted_at_comes_from_start_date(self, company):
        job = workday.build_job(WORKDAY_JOB, company, "nvidia:wd5:Site")
        assert job.posted_at is not None
        assert job.posted_at.strftime("%Y-%m-%d") == "2026-07-30"

    def test_country_name_backfills_code_and_region(self, company):
        """Workday sends a country display name, never an ISO code."""
        job = workday.build_job(
            {
                **WORKDAY_JOB,
                "location": "Yokneam",
                "locationsText": "Yokneam",
                "country": {"descriptor": "United States of America"},
            },
            company,
            "nvidia:wd5:Site",
        )
        assert job.city is None, "unlisted city should not resolve"
        assert job.country_code == "US"
        assert job.region == "north_america"

    def test_unrecognised_country_leaves_code_unset(self, company):
        job = workday.build_job(
            {
                **WORKDAY_JOB,
                "location": "Nowhere",
                "locationsText": "Nowhere",
                "country": {"descriptor": "Atlantis"},
            },
            company,
            "nvidia:wd5:Site",
        )
        assert job.country_code is None
        assert job.region is None

    def test_multi_site_placeholder_location_is_dropped(self, company):
        job = workday.build_job(
            {**WORKDAY_JOB, "location": "", "locationsText": "2 Locations"},
            company,
            "nvidia:wd5:Site",
        )
        assert job.location_raw == ""

    def test_part_time_maps_to_parttime(self, company):
        job = workday.build_job(
            {**WORKDAY_JOB, "timeType": "Part time"}, company, "nvidia:wd5:Site"
        )
        assert job.job_type == "parttime"

    def test_source_url_falls_back_to_constructed_path(self, company):
        job = workday.build_job({**WORKDAY_JOB, "externalUrl": None}, company, "nvidia:wd5:Site")
        assert job.source_url == (
            "https://nvidia.wd5.myworkdayjobs.com/Site"
            "/job/US-CA-Santa-Clara/Senior-ML-Engineer_JR2020107"
        )


RIPPLING_JOB = {
    "uuid": "4cda73f6-3a21-42c3-8bbb-a2a52354df93",
    "name": "Senior Backend Engineer ",
    "url": "https://ats.rippling.com/moov/jobs/4cda73f6",
    # merged in from the per-job detail fetch
    "description": {"company": "<p>We are Moov.</p>", "role": "<p>Write Go services on AWS.</p>"},
    "workLocations": ["Remote, United States"],
    "department": {"name": "Engineering", "base_department": "Engineering"},
    "employmentType": {"label": "SALARIED_FT", "id": "Salaried, full-time"},
    "createdOn": "2026-07-21T10:18:02.324000-07:00",
    "board": {"slug": "moov", "logo": {"url": "https://cdn.example/logo.png"}},
    "companyName": "Moov",
}


class TestRippling:
    def test_job_id_is_uuid(self):
        assert rippling.extract_job_id(RIPPLING_JOB) == RIPPLING_JOB["uuid"]

    def test_build_job_joins_description_parts(self, company):
        job = rippling.build_job(RIPPLING_JOB, company, "moov")
        assert "Write Go services on AWS." in job.description
        assert "We are Moov." in job.description
        assert "<p>" not in job.description

    def test_build_job_classifies(self, company):
        job = rippling.build_job(RIPPLING_JOB, company, "moov")
        assert job.title == "Senior Backend Engineer"
        assert job.role_category == "engineering"
        assert job.role_subcategory == "backend"
        assert job.seniority == "senior"
        assert job.department == "Engineering"
        assert job.job_type == "fulltime"

    def test_employment_type_codes(self, company):
        for code, expected in [
            ("HOURLY_PT", "parttime"),
            ("CONTRACTOR", "contract"),
            ("INTERN", "intern"),
        ]:
            job = rippling.build_job(
                {**RIPPLING_JOB, "employmentType": {"label": code, "id": ""}},
                company,
                "moov",
            )
            assert job.job_type == expected, code

    def test_remote_location(self, company):
        job = rippling.build_job(RIPPLING_JOB, company, "moov")
        assert job.is_remote is True

    def test_country_from_location_tail(self, company):
        """ "City, Country" strings still pin the country when the city is unlisted."""
        job = rippling.build_job(
            {**RIPPLING_JOB, "workLocations": ["Sarnia, Canada"]}, company, "moov"
        )
        assert job.city is None
        assert job.country_code == "CA"
        assert job.region == "north_america"

    def test_unrecognised_location_tail_leaves_code_unset(self, company):
        job = rippling.build_job(
            {**RIPPLING_JOB, "workLocations": ["Somewhere, Atlantis"]}, company, "moov"
        )
        assert job.country_code is None
        assert job.region is None

    def test_falls_back_to_list_shape_when_detail_missing(self, company):
        """The list payload nests location/department differently from the detail payload."""
        listing = {
            "uuid": RIPPLING_JOB["uuid"],
            "name": "Data Analyst",
            "url": RIPPLING_JOB["url"],
            "department": {"id": "Analytics", "label": "Analytics"},
            "workLocation": {"label": "London, United Kingdom", "id": "London"},
        }
        job = rippling.build_job(listing, company, "moov")
        assert job.department == "Analytics"
        assert job.city == "London"
        assert job.description == ""

    def test_build_job_backfills_company_logo(self, company):
        rippling.build_job(RIPPLING_JOB, company, "moov")
        assert company.logo_url == "https://cdn.example/logo.png"


class TestRegistration:
    @pytest.mark.parametrize("ats", ["workday", "teamtailor", "rippling"])
    def test_ingester_is_registered(self, ats):
        assert ats in INGESTERS
        assert INGESTERS[ats].ats_type == ats

    @pytest.mark.parametrize("ats", ["workday", "teamtailor", "rippling"])
    def test_seed_file_is_well_formed(self, ats):
        entries = json.loads((DATA_DIR / f"companies_{ats}.json").read_text(encoding="utf-8"))
        assert entries
        slugs = [e["slug"] for e in entries]
        assert len(slugs) == len(set(slugs)), "seed slugs must be unique"
        for entry in entries:
            assert entry["name"] and entry["slug"] and entry["ats_slug"]

    def test_workday_seed_slugs_are_composite(self):
        entries = json.loads((DATA_DIR / "companies_workday.json").read_text(encoding="utf-8"))
        for entry in entries:
            tenant, wd, board = _parse_slug(entry["ats_slug"])
            assert wd.startswith("wd")
            assert entry["slug"] == tenant


def test_seed_stubs_load_from_data_dir():
    """discover() defaults to the curated seed file for ATS with no public directory."""
    stubs = workday._load_seed_stubs()
    assert stubs
    assert all(s.ats_type == "workday" for s in stubs)
    assert all(":" in s.ats_slug and ":" not in s.slug for s in stubs)
