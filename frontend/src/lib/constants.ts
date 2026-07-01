export const GITHUB_REPO = "areebahmeddd/jobdex";

export const API_BASE =
  (import.meta.env.VITE_API_URL as string | undefined) ??
  "https://jobdex-api.1mindlabs.org";

export const HOME_CENTER: [number, number] = [20, 0];
export const MAP_MAX_ZOOM = 19;
export const MAP_MIN_ZOOM = Math.ceil(MAP_MAX_ZOOM * 0.1);
export const HOME_ZOOM = (MAP_MAX_ZOOM * 20) / 100;

export const ROLE_OPTIONS: { label: string; value: string | null }[] = [
  { label: "All roles", value: null },
  { label: "Engineering", value: "engineering" },
  { label: "Product", value: "product" },
  { label: "Design", value: "design" },
  { label: "Data", value: "data" },
  { label: "Marketing", value: "marketing" },
  { label: "Sales", value: "sales" },
  { label: "Operations", value: "operations" },
  { label: "Finance", value: "finance" },
  { label: "Healthcare", value: "healthcare" },
  { label: "Hospitality", value: "hospitality" },
];
