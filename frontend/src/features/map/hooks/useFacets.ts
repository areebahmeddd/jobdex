import { fetchJobFacets } from "@/api/jobs";
import type { ApiParams, JobFacets } from "@/types";
import { useEffect, useRef, useState } from "react";

export function useFacets(params: ApiParams, enabled: boolean) {
  const [facets, setFacets] = useState<JobFacets | null>(null);
  const [loading, setLoading] = useState(false);
  const latest = useRef(params);
  latest.current = params;
  const key = JSON.stringify(params);

  useEffect(() => {
    if (!enabled) return;
    const ac = new AbortController();
    setLoading(true);
    fetchJobFacets(latest.current, ac.signal)
      .then(setFacets)
      .catch(() => {})
      .finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
    return () => ac.abort();
  }, [key, enabled]);

  return { facets, loading };
}
