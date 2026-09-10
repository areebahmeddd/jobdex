import type {
  ApiParams,
  CompanyDetail,
  CompanyJobsData,
  PaginatedCompaniesData,
} from "@/types";
import { apiFetch } from "./client";

export function fetchCompanies(
  params: ApiParams,
  signal?: AbortSignal,
): Promise<PaginatedCompaniesData> {
  return apiFetch<PaginatedCompaniesData>("/companies", params, signal);
}

export function fetchCompanyDetail(
  slug: string,
  signal?: AbortSignal,
): Promise<CompanyDetail> {
  return apiFetch<CompanyDetail>(
    `/companies/${encodeURIComponent(slug)}`,
    {},
    signal,
  );
}

export function fetchCompanyJobs(
  slug: string,
  params: ApiParams,
  signal?: AbortSignal,
): Promise<CompanyJobsData> {
  return apiFetch<CompanyJobsData>(
    `/companies/${encodeURIComponent(slug)}/jobs`,
    params,
    signal,
  );
}
