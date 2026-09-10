import type {
  ApiParams,
  JobDetail,
  JobFacets,
  PaginatedJobsData,
} from "@/types";
import { apiFetch } from "./client";

export function fetchJobs(
  params: ApiParams,
  signal?: AbortSignal,
): Promise<PaginatedJobsData> {
  return apiFetch<PaginatedJobsData>("/jobs", params, signal);
}

export function fetchJobDetail(
  jobId: string,
  signal?: AbortSignal,
): Promise<JobDetail> {
  return apiFetch<JobDetail>(`/jobs/${encodeURIComponent(jobId)}`, {}, signal);
}

export function fetchJobFacets(
  params: ApiParams,
  signal?: AbortSignal,
): Promise<JobFacets> {
  return apiFetch<JobFacets>("/jobs/facets", params, signal);
}
