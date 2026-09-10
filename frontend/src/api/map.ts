import type { ApiParams, MapCitiesData, MapCompaniesData } from "@/types";
import { apiFetch } from "./client";

export function fetchMapCities(
  params: ApiParams,
  signal?: AbortSignal,
): Promise<MapCitiesData> {
  return apiFetch<MapCitiesData>("/map/cities", params, signal);
}

export function fetchMapCompanies(
  params: ApiParams,
  signal?: AbortSignal,
): Promise<MapCompaniesData> {
  return apiFetch<MapCompaniesData>("/map/companies", params, signal);
}
