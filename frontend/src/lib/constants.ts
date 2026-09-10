export const GITHUB_REPO = "areebahmeddd/jobdex";

export const API_BASE =
  (import.meta.env.VITE_API_URL as string | undefined) ??
  "https://jobdex-api.1mindlabs.org";

export const CARTO_KEY = import.meta.env.VITE_CARTO_KEY as string | undefined;

export const HOME_CENTER: [number, number] = [20, 0];
export const MAP_MAX_ZOOM = 19;
export const MAP_MIN_ZOOM = Math.ceil(MAP_MAX_ZOOM * 0.1);
export const HOME_ZOOM = (MAP_MAX_ZOOM * 20) / 100;
