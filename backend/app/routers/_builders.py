from app.models import City, Company, Job
from app.schemas import CityResponse, CompanyResponse, JobDetailResponse, JobResponse


def build_job_response(job: Job, company: Company) -> JobResponse:
    """Build a JobResponse from a Job ORM object and its associated Company."""
    data = JobResponse.model_validate(job)
    data.company_name = company.name
    data.company_slug = company.slug
    data.company_logo_url = company.logo_url
    return data


def build_job_detail_response(job: Job, company: Company) -> JobDetailResponse:
    """Build a JobDetailResponse including the full description from a Job ORM object."""
    data = JobDetailResponse.model_validate(job)
    data.company_name = company.name
    data.company_slug = company.slug
    data.company_logo_url = company.logo_url
    return data


def build_company_response(
    company: Company, job_count: int, categories: list[str]
) -> CompanyResponse:
    """Build a CompanyResponse with job count and open role categories attached."""
    data = CompanyResponse.model_validate(company)
    data.job_count = job_count
    data.open_role_categories = sorted(categories)
    return data


def build_city_response(city: City, job_count: int, company_count: int) -> CityResponse:
    """Build a CityResponse from a City ORM object and its job and company counts."""
    return CityResponse(
        id=city.id,
        name=city.name,
        slug=city.slug,
        country=city.country,
        country_code=city.country_code,
        region=city.region,
        latitude=city.latitude,
        longitude=city.longitude,
        is_featured=city.is_featured,
        job_count=job_count,
        company_count=company_count,
    )
