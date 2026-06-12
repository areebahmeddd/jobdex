import { CityPin, Company, Job, JobDetail, MapCompanyPin } from "../types/api";

const BASE_URL = "/api";

/**
 * Helper to construct fetch requests and handle API errors cleanly.
 */
async function fetcher<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(
      `API Error on ${path}: ${response.status} ${response.statusText}`,
    );
  }

  return response.json() as Promise<T>;
}

// 1. GET /map/cities
export async function fetchCityPins(): Promise<CityPin[]> {
  const res = await fetcher<{ cities: CityPin[] }>("/map/cities");
  return res.cities;
}

// 2. GET /map/companies?lat_min&lat_max&lng_min&lng_max&role&is_remote&country_code
export interface CompanyPinsFilters {
  lat_min?: number;
  lat_max?: number;
  lng_min?: number;
  lng_max?: number;
  role?: string | null;
  is_remote?: boolean | null;
  country_code?: string | null;
}

export async function fetchCompanyPins(
  filters: CompanyPinsFilters,
): Promise<MapCompanyPin[]> {
  const params = new URLSearchParams();
  if (filters.lat_min !== undefined)
    params.append("lat_min", filters.lat_min.toString());
  if (filters.lat_max !== undefined)
    params.append("lat_max", filters.lat_max.toString());
  if (filters.lng_min !== undefined)
    params.append("lng_min", filters.lng_min.toString());
  if (filters.lng_max !== undefined)
    params.append("lng_max", filters.lng_max.toString());
  if (filters.role) params.append("role", filters.role);
  if (filters.is_remote !== undefined && filters.is_remote !== null) {
    params.append("is_remote", filters.is_remote.toString());
  }
  if (filters.country_code) params.append("country_code", filters.country_code);

  const queryStr = params.toString();
  const res = await fetcher<{ companies: MapCompanyPin[] }>(
    `/map/companies${queryStr ? "?" + queryStr : ""}`,
  );
  return res.companies;
}

// 3. GET /jobs?city&role_category&seniority&is_remote&cursor&limit
export interface FetchJobsFilters {
  city?: string | null;
  role_category?: string | null;
  seniority?: string | null;
  is_remote?: boolean | null;
  limit?: number;
}

export interface PaginatedJobsResponse {
  jobs: Job[];
  next_cursor: string | null;
  total?: number;
}

export async function fetchJobs(
  filters: FetchJobsFilters,
  cursor?: string | null,
  limit = 20,
): Promise<PaginatedJobsResponse> {
  const params = new URLSearchParams();
  if (filters.city) params.append("city", filters.city);
  if (filters.role_category)
    params.append("role_category", filters.role_category);
  if (filters.seniority) params.append("seniority", filters.seniority);
  if (filters.is_remote !== undefined && filters.is_remote !== null) {
    params.append("is_remote", filters.is_remote.toString());
  }
  if (cursor) params.append("cursor", cursor);
  params.append("limit", limit.toString());

  const queryStr = params.toString();

  const result = await fetcher<PaginatedJobsResponse>(
    `/jobs${queryStr ? "?" + queryStr : ""}`,
  );
  return result;
}

// 4. GET /jobs/{id}
export async function fetchJobDetail(id: string): Promise<JobDetail> {
  return fetcher<JobDetail>(`/jobs/${id}`);
}

// 5. GET /companies/{slug}
export async function fetchCompanyDetail(slug: string): Promise<Company> {
  return fetcher<Company>(`/companies/${slug}`);
}

// 6. GET /companies/{slug}/jobs?limit=6
export async function fetchCompanyJobs(
  slug: string,
  limit = 6,
): Promise<Job[]> {
  const res = await fetcher<{ jobs: Job[] }>(
    `/companies/${slug}/jobs?limit=${limit}`,
  );
  return res.jobs;
}

// 7. GET /cities?featured_only=true
export async function fetchFeaturedCities(): Promise<CityPin[]> {
  const res = await fetcher<{ cities: CityPin[] }>(
    "/cities?featured_only=true",
  );
  return res.cities;
}

// 8. GET /health
export interface HealthStatus {
  status: string;
}

export async function fetchHealth(): Promise<HealthStatus> {
  return fetcher<HealthStatus>("/health");
}

// 9. GET /search?city&role&country_code&region&is_remote&limit&offset
export interface SearchFilters {
  city?: string | null;
  role?: string | null;
  country_code?: string | null;
  region?: string | null;
  is_remote?: boolean | null;
  limit?: number;
  offset?: number;
}

export interface SearchResponse {
  jobs: Job[];
  companies: Company[];
  total_jobs: number;
}

export async function searchJobsAndCompanies(
  filters: SearchFilters,
): Promise<SearchResponse> {
  const params = new URLSearchParams();
  if (filters.city) params.append("city", filters.city);
  if (filters.role) params.append("role", filters.role);
  if (filters.country_code) params.append("country_code", filters.country_code);
  if (filters.region) params.append("region", filters.region);
  if (filters.is_remote !== undefined && filters.is_remote !== null) {
    params.append("is_remote", filters.is_remote.toString());
  }
  if (filters.limit) params.append("limit", filters.limit.toString());
  if (filters.offset) params.append("offset", filters.offset.toString());

  const queryStr = params.toString();
  return fetcher<SearchResponse>(`/search${queryStr ? "?" + queryStr : ""}`);
}
