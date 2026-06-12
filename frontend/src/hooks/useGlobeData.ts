import { useQuery } from "@tanstack/react-query";
import {
  CompanyPinsFilters,
  fetchCityPins,
  fetchCompanyPins,
  fetchFeaturedCities,
} from "../lib/api";

/**
 * Hook to retrieve all city pins.
 */
export function useCityPins() {
  return useQuery({
    queryKey: ["cityPins"],
    queryFn: fetchCityPins,
    staleTime: 1000 * 60 * 10, // 10 minutes cache
  });
}

/**
 * Hook to retrieve initial featured cities.
 */
export function useFeaturedCities() {
  return useQuery({
    queryKey: ["featuredCities"],
    queryFn: fetchFeaturedCities,
    staleTime: 1000 * 60 * 15, // 15 minutes cache
  });
}

/**
 * Hook to retrieve active company logos inside viewport bounds.
 * Active only when zoomed level is 'city'.
 */
export function useCompanyPins(filters: CompanyPinsFilters, enabled: boolean) {
  return useQuery({
    queryKey: ["companyPins", filters],
    queryFn: () => fetchCompanyPins(filters),
    enabled:
      enabled &&
      !!filters.lat_min &&
      !!filters.lat_max &&
      !!filters.lng_min &&
      !!filters.lng_max,
    staleTime: 1000 * 60 * 2, // 2 minutes cache
    placeholderData: (previousData) => previousData, // smooth transitions
  });
}
