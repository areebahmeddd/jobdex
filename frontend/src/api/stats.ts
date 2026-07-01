import type { StatsData } from "@/types";
import { apiFetch } from "./client";

export function fetchStats(signal?: AbortSignal): Promise<StatsData> {
  return apiFetch<StatsData>("/stats", {}, signal);
}
