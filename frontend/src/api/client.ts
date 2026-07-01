import { API_BASE } from "@/lib/constants";

export async function apiFetch<T>(
  path: string,
  params?: Record<string, string>,
  signal?: AbortSignal,
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, v);
    }
  }
  const res = await fetch(url.toString(), { signal });
  if (!res.ok) return Promise.reject(new Error(`HTTP ${res.status}`));
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(
      (detail as { detail?: string })?.detail ?? `HTTP ${res.status}`,
    );
  }
  return res.json() as Promise<T>;
}
