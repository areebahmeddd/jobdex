import type { JobDetail, PaginatedJobsData } from "@/types";
import { apiFetch } from "./client";

export function fetchJobs(
  params: Record<string, string>,
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
