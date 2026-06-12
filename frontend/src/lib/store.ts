import { create } from "zustand";

export interface GlobeStore {
  zoomLevel: "world" | "country" | "city";
  viewportBounds: {
    lat_min: number;
    lat_max: number;
    lng_min: number;
    lng_max: number;
  } | null;
  activeCity: string | null;
  activeCityCoords: { lat: number; lng: number } | null;
  activeCitySlug: string | null;
  activeCountryCode: string | null;
  activeRegion: string | null;
  activeRole: string | null;
  activeIsRemote: boolean | null;
  activeSeniority: string | null;
  selectedJobId: string | null;
  isDrawerOpen: boolean;

  setZoomLevel: (
    level: "world" | "country" | "city",
    bounds?: GlobeStore["viewportBounds"],
  ) => void;
  setActiveCity: (
    name: string | null,
    coords?: { lat: number; lng: number },
    slug?: string,
  ) => void;
  setFilter: (
    key: keyof Pick<
      GlobeStore,
      | "activeRole"
      | "activeIsRemote"
      | "activeSeniority"
      | "activeCountryCode"
      | "activeRegion"
    >,
    value: string | boolean | null,
  ) => void;
  clearFilters: () => void;
  openJob: (jobId: string) => void;
  closeJob: () => void;
}

// Read initial filters from browser URL params on load
const getInitialParams = () => {
  if (typeof window === "undefined") return {};

  const params = new URLSearchParams(window.location.search);
  const activeCity = params.get("city") || null;
  const activeRole = params.get("role") || null;
  const activeCountryCode = params.get("country_code") || null;

  return {
    activeCity,
    activeRole,
    activeCountryCode,
  };
};

const initialFromUrl = getInitialParams();

export const useGlobeStore = create<GlobeStore>((set, get) => ({
  zoomLevel: "world",
  viewportBounds: null,
  activeCity: initialFromUrl.activeCity ?? null,
  activeCityCoords: null,
  activeCitySlug: null,
  activeCountryCode: initialFromUrl.activeCountryCode ?? null,
  activeRegion: null,
  activeRole: initialFromUrl.activeRole ?? null,
  activeIsRemote: null,
  activeSeniority: null,
  selectedJobId: null,
  isDrawerOpen: false,

  setZoomLevel: (level, bounds = null) => {
    set({ zoomLevel: level });
    if (bounds) {
      set({ viewportBounds: bounds });
    }
  },

  setActiveCity: (name, coords = undefined, slug = undefined) => {
    set({
      activeCity: name,
      activeCityCoords: coords,
      activeCitySlug: slug || null,
    });

    // Sync URL parameters
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (name) {
        params.set("city", name);
      } else {
        params.delete("city");
      }
      const newUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`;
      window.history.pushState({}, "", newUrl);
    }
  },

  setFilter: (key, value) => {
    set({ [key]: value } as any);

    // Sync to URL parameters for matching state parameters
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);

      const valStr = value !== null && value !== undefined ? String(value) : "";

      if (key === "activeRole") {
        if (valStr) params.set("role", valStr);
        else params.delete("role");
      } else if (key === "activeCountryCode") {
        if (valStr) params.set("country_code", valStr);
        else params.delete("country_code");
      }

      const newUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`;
      window.history.pushState({}, "", newUrl);
    }
  },

  clearFilters: () => {
    set({
      activeCity: null,
      activeCityCoords: null,
      activeCitySlug: null,
      activeCountryCode: null,
      activeRegion: null,
      activeRole: null,
      activeIsRemote: null,
      activeSeniority: null,
    });

    // Clear URL params
    if (typeof window !== "undefined") {
      window.history.pushState({}, "", window.location.pathname);
    }
  },

  openJob: (jobId) => {
    set({ selectedJobId: jobId, isDrawerOpen: true });
  },

  closeJob: () => {
    set({ selectedJobId: null, isDrawerOpen: false });
  },
}));
