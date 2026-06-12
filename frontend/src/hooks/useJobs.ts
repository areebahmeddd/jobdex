import { useInfiniteQuery } from "@tanstack/react-query";
import { fetchJobs, FetchJobsFilters, PaginatedJobsResponse } from "../lib/api";

/**
 * Hook for paginating through matching jobs based on selected search filters.
 */
export function useJobsList(filters: FetchJobsFilters) {
  return useInfiniteQuery<
    PaginatedJobsResponse,
    Error,
    any,
    any,
    string | null
  >({
    queryKey: ["jobs", filters],
    queryFn: ({ pageParam }) => {
      return fetchJobs(filters, pageParam);
    },
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => {
      return lastPage.next_cursor ? lastPage.next_cursor : undefined;
    },
    staleTime: 1000 * 30, // 30 seconds stale time
  });
}
