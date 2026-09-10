import { API_BASE } from "@/lib/constants";
import type { ApiParams } from "@/types";

type ApiReachabilityListener = (reachable: boolean) => void;

const listeners = new Set<ApiReachabilityListener>();

export function onApiReachability(listener: ApiReachabilityListener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function report(reachable: boolean) {
  for (const listener of listeners) listener(reachable);
}

function buildUrl(path: string, params?: ApiParams) {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined) continue;
      if (Array.isArray(value)) {
        for (const item of value) url.searchParams.append(key, item);
      } else {
        url.searchParams.set(key, value);
      }
    }
  }
  return url.toString();
}

export async function apiFetch<T>(
  path: string,
  params?: ApiParams,
  signal?: AbortSignal,
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(buildUrl(path, params), { signal });
  } catch (err) {
    if (!signal?.aborted) report(false);
    throw err;
  }
  report(true);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    report(false);
    throw err;
  }
  report(true);
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(
      (detail as { detail?: string })?.detail ?? `HTTP ${res.status}`,
    );
  }
  return res.json() as Promise<T>;
}
