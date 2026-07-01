import type { MapCitiesData, MapCompaniesData } from "@/types";
import { apiFetch } from "./client";

export function fetchMapCities(
  params: Record<string, string>,
  signal?: AbortSignal,
): Promise<MapCitiesData> {
  return apiFetch<MapCitiesData>("/map/cities", params, signal);
}

export function fetchMapCompanies(
  params: Record<string, string>,
  signal?: AbortSignal,
): Promise<MapCompaniesData> {
  return apiFetch<MapCompaniesData>("/map/companies", params, signal);
}
