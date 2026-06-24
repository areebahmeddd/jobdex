export { GITHUB_REPO } from "@/lib/constants";

export const HOME_CENTER: [number, number] = [20, 0];
export const MAP_MAX_ZOOM = 19;
export const HOME_ZOOM_PERCENT = 20;
export const HOME_ZOOM = (MAP_MAX_ZOOM * HOME_ZOOM_PERCENT) / 100;
export const COMPANY_ZOOM_THRESHOLD = 9;
export const API_BASE =
  (import.meta.env.VITE_API_URL as string | undefined) ??
  "http://localhost:8000";

export const ROLE_OPTIONS: { label: string; value: string | null }[] = [
  { label: "All roles", value: null },
  { label: "Engineering", value: "engineering" },
  { label: "Design", value: "design" },
  { label: "Product", value: "product" },
  { label: "Data", value: "data" },
  { label: "Marketing", value: "marketing" },
  { label: "Sales", value: "sales" },
  { label: "Finance", value: "finance" },
  { label: "Operations", value: "operations" },
];
