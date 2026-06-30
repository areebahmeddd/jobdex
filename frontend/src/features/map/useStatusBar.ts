import { useEffect, useState } from "react";
import { API_BASE, GITHUB_REPO } from "./constants";
import type { StatsData } from "./types";

type StatusBar = {
  connected: boolean | null;
  stars: number | null;
  indexedStats: { jobs: number; cities: number } | null;
};

export function useStatusBar(): StatusBar {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [stars, setStars] = useState<number | null>(null);
  const [indexedStats, setIndexedStats] = useState<{
    jobs: number;
    cities: number;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) })
      .then((r) => {
        if (!cancelled) setConnected(r.ok);
      })
      .catch(() => {
        if (!cancelled) setConnected(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    fetch(`https://api.github.com/repos/${GITHUB_REPO}`)
      .then((r) => r.json())
      .then((d) => {
        if (typeof d.stargazers_count === "number")
          setStars(d.stargazers_count);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/stats`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d: StatsData) => {
        setIndexedStats({ jobs: d.active_jobs, cities: d.cities_with_jobs });
      })
      .catch(() => {});
  }, []);

  return { connected, stars, indexedStats };
}
