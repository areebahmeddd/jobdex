import { onApiReachability } from "@/api/client";
import { fetchStats } from "@/api/stats";
import { API_BASE, GITHUB_REPO } from "@/lib/constants";
import type { StatsData } from "@/types";
import { useEffect, useState } from "react";

const HEALTH_TIMEOUT_MS = 4000;

type StatusBar = {
  connected: boolean | null;
  stars: number | null;
  stats: StatsData | null;
};

export function useStatusBar(): StatusBar {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [stars, setStars] = useState<number | null>(null);
  const [stats, setStats] = useState<StatsData | null>(null);

  useEffect(() => {
    let disposed = false;
    const unsubscribe = onApiReachability((reachable) => {
      if (!disposed) setConnected(reachable);
    });

    fetch(`${API_BASE}/health`, {
      signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
    })
      .then((res) => {
        if (!disposed) setConnected(res.ok);
      })
      .catch(() => {});

    return () => {
      disposed = true;
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    fetch(`https://api.github.com/repos/${GITHUB_REPO}`)
      .then((res) => res.json())
      .then((d: { stargazers_count?: number }) => {
        if (typeof d.stargazers_count === "number")
          setStars(d.stargazers_count);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    let disposed = false;
    const ac = new AbortController();
    fetchStats(ac.signal)
      .then((d) => {
        if (!disposed) setStats(d);
      })
      .catch(() => {});
    return () => {
      disposed = true;
      ac.abort();
    };
  }, []);

  return { connected, stars, stats };
}
