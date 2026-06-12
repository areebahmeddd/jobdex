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

    location_raw: str | None = None
    city: str | None = None
    country: str | None = None
    country_code: str | None = None
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_remote: bool = False
    remote_type: str | None = None

    job_type: str | None = None
    seniority: str | None = None
    role_category: str | None = None
    role_subcategory: str | None = None
    tech_stack: list[str] = []
    department: str | None = None

    source_url: str
    ats_type: str | None = None
    posted_at: datetime | None = None
    is_active: bool = True
    first_seen_at: datetime | None = None

    @computed_field  # type: ignore[misc]
    @property
    def location_display(self) -> str:
        """Build a human-readable location label for display in job listings."""
        if self.is_remote and not self.city:
            return "Remote"
        parts = [p for p in [self.city, self.country_code] if p]
        label = ", ".join(parts)
        if self.is_remote and label:
            return f"{label} (Remote OK)"
        return label or "Unknown"


class JobDetailResponse(JobResponse):
    description: str | None = None


# Companies


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
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
    logo_url: str | None = None
    ats_type: str | None = None

    job_count: int = 0
    open_role_categories: list[str] = []

    last_crawled_at: datetime | None = None


class CompanyDetailResponse(CompanyResponse):
    pass


# Cities


class CityResponse(BaseModel):
    id: str
    name: str
    slug: str
    country: str | None = None
    country_code: str | None = None
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    is_featured: bool = False
    job_count: int = 0
    company_count: int = 0


# Search


class SearchResponse(BaseModel):
    companies: list[CompanyResponse] = []
    jobs: list[JobResponse] = []
    total_companies: int = 0
    total_jobs: int = 0
    offset: int = 0
    limit: int = 20
    filters: dict = {}


# Ingestion


class IngestResponse(BaseModel):
    company_slug: str
    ats_type: str
    total_fetched: int = 0
    new_jobs: int = 0
    updated_jobs: int = 0
    deactivated_jobs: int = 0  # jobs on previous board no longer returned by ATS
    errors: list[str] = []


class DiscoverResponse(BaseModel):
    company_slug: str
    ats_type: str | None = None
    discovered: bool = False
    message: str = ""
    ingest_result: IngestResponse | None = None


# Stats


class StatsResponse(BaseModel):
    total_companies: int
    total_jobs: int
    active_jobs: int
    total_cities: int
    cities_with_jobs: int
    role_categories: dict
    top_cities: list[dict]
    top_regions: list[dict]
    ats_breakdown: dict
