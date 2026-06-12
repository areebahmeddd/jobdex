export const HOME_CENTER: [number, number] = [20, 0];
export const HOME_ZOOM = 2;
export const COMPANY_ZOOM_THRESHOLD = 9;
export const GITHUB_REPO = "areebahmeddd/jobdex";
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
