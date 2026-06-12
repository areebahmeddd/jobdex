import { useQuery } from "@tanstack/react-query";
import {
  fetchCompanyDetail,
  fetchCompanyJobs,
  fetchJobDetail,
} from "../lib/api";

/**
 * Hook to retrieve full job description and structural attributes.
 */
export function useJobDetailQuery(jobId: string | null) {
  return useQuery({
    queryKey: ["jobDetail", jobId],
    queryFn: () => fetchJobDetail(jobId!),
    enabled: !!jobId,
    staleTime: 1000 * 60 * 5, // 5 minutes cache
  });
}

/**
 * Hook to retrieve the corporate profiles of employer companies.
 */
export function useCompanyDetailQuery(slug: string | null) {
  return useQuery({
    queryKey: ["companyDetail", slug],
    queryFn: () => fetchCompanyDetail(slug!),
    enabled: !!slug,
    staleTime: 1000 * 60 * 10, // 10 minutes cache
  });
}

/**
 * Hook to retrieve supplementary active job listings from the same company.
 */
export function useCompanyJobsQuery(slug: string | null, limit = 6) {
  return useQuery({
    queryKey: ["companyJobs", slug, limit],
    queryFn: () => fetchCompanyJobs(slug!, limit),
    enabled: !!slug,
    staleTime: 1000 * 60 * 5, // 5 minutes cache
  });
}
