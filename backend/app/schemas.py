from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

# Jobs


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    company_name: str = ""
    company_slug: str = ""
    company_logo_url: str | None = None

    title: str
    description_snippet: str | None = None

    city: str | None = None
    country: str | None = None
    country_code: str | None = None
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_remote: bool = False
    remote_type: str | None = None

    role_category: str | None = None
    role_subcategory: str | None = None
    seniority: str | None = None
    job_type: str | None = None
    department: str | None = None
    tech_stack: list[str] = []

    source_url: str
    ats_type: str | None = None
    posted_at: datetime | None = None

    @computed_field  # type: ignore[misc]
    @property
    def location_display(self) -> str:
        """Build a human-readable location label for display in job listings."""
        if self.is_remote and not self.city:
            return "Remote"
        parts = [part for part in [self.city, self.country_code] if part]
        label = ", ".join(parts)
        if self.is_remote and label:
            return f"{label} (Remote OK)"
        return label or "Unknown"


class JobDetailResponse(JobResponse):
    location_raw: str | None = None
    description: str | None = None


class PaginatedJobsResponse(BaseModel):
    jobs: list[JobResponse]
    total: int | None = None
    limit: int
    offset: int | None = None
    next_cursor: str | None = None


# Companies


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    logo_url: str | None = None
    description: str | None = None
    website: str | None = None

    city: str | None = None
    country: str | None = None
    country_code: str | None = None
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    industry: list[str] = []
    stage: str | None = None
    founded_year: int | None = None
    ats_type: str | None = None
    last_crawled_at: datetime | None = None

    job_count: int = 0
    open_role_categories: list[str] = []


class CompanyDetailResponse(CompanyResponse):
    wikidata_id: str | None = None
    enriched_at: datetime | None = None
    founders: list[dict] | None = None
    key_investors: list[dict] | None = None
    total_funding_usd: int | None = None
    funding_stage: str | None = None
    business_model: str | None = None
    headcount_range: str | None = None
    benefits: list[dict] | None = None
    office_address: str | None = None
    social_links: dict | None = None

    work_modes: list[str] = []
    departments: list[str] = []


class CompanyBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    logo_url: str | None = None
    city: str | None = None
    country_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class PaginatedCompaniesResponse(BaseModel):
    companies: list[CompanyResponse]
    total: int
    limit: int
    offset: int


class CompanyJobsResponse(BaseModel):
    company: CompanyBriefResponse
    jobs: list[JobResponse]
    total: int
    limit: int
    offset: int


# Cities


class CityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    country: str | None = None
    country_code: str | None = None
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    job_count: int = 0
    company_count: int = 0


class PaginatedCitiesResponse(BaseModel):
    cities: list[CityResponse]
    total: int
    limit: int
    offset: int


# Search


class SearchResponse(BaseModel):
    companies: list[CompanyResponse] = []
    jobs: list[JobResponse] = []
    total_companies: int = 0
    total_jobs: int = 0
    offset: int = 0
    limit: int = 20


# Ingestion


class IngestResponse(BaseModel):
    company_slug: str
    ats_type: str
    total_fetched: int = 0
    new_jobs: int = 0
    updated_jobs: int = 0
    deactivated_jobs: int = 0
    errors: list[str] = []


class EnrichResponse(BaseModel):
    slug: str
    name: str
    wikidata_id: str | None = None
    updated_fields: list[str] = []
    enriched_at: datetime | None = None


# Stats


class CityStatEntry(BaseModel):
    city: str
    job_count: int


class RegionStatEntry(BaseModel):
    region: str
    job_count: int


class StatsResponse(BaseModel):
    total_companies: int
    total_jobs: int
    active_jobs: int
    total_cities: int
    cities_with_jobs: int
    role_categories: dict
    top_cities: list[CityStatEntry]
    top_regions: list[RegionStatEntry]
    ats_breakdown: dict


# Map


class MapCompanyPin(BaseModel):
    id: str
    name: str
    slug: str
    city: str | None = None
    country_code: str | None = None
    region: str | None = None
    latitude: float
    longitude: float
    industry: list[str] = []
    logo_url: str | None = None
    job_count: int = 0


class MapCompaniesResponse(BaseModel):
    companies: list[MapCompanyPin]
    total: int


class MapCityPin(BaseModel):
    name: str
    slug: str
    latitude: float
    longitude: float
    country_code: str | None = None
    region: str | None = None
    job_count: int = 0
    company_count: int = 0


class MapCitiesResponse(BaseModel):
    cities: list[MapCityPin]
    total: int


class OfficePin(BaseModel):
    city: str
    country_code: str | None = None
    latitude: float
    longitude: float
    job_count: int = 0


class CompanyOfficesResponse(BaseModel):
    offices: list[OfficePin]
