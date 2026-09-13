import {
  FILTER_GROUPS,
  labelFor,
  postedLabel,
  type FilterKey,
  type SortValue,
} from "@/lib/filters";
import type { ApiParams } from "@/types";
import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export type PanelMode = "jobs" | "companies";

export type FilterChip = {
  id: string;
  label: string;
  group?: string;
  remove: () => void;
};

const MAX_QUERY_LENGTH = 200;
const MAX_VALUES_PER_GROUP = 25;

const PARAM = {
  q: "q",
  city: "city",
  country: "country",
  posted: "posted",
  sort: "sort",
  view: "view",
  job: "job",
  company: "co",
} as const;

function readList(params: URLSearchParams, key: FilterKey): string[] {
  const values = params
    .getAll(key)
    .map((v) => v.trim().toLowerCase())
    .filter(Boolean);
  return [...new Set(values)].slice(0, MAX_VALUES_PER_GROUP);
}

export function useJobFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const q = (searchParams.get(PARAM.q) ?? "").slice(0, MAX_QUERY_LENGTH);
  const city = searchParams.get(PARAM.city) || null;
  const countryRaw = searchParams.get(PARAM.country) || "";
  const country = /^[A-Za-z]{2}$/.test(countryRaw)
    ? countryRaw.toUpperCase()
    : null;
  const jobId = searchParams.get(PARAM.job) || null;
  const companySlug = searchParams.get(PARAM.company) || null;

  const selections = useMemo(() => {
    const entries = FILTER_GROUPS.map(
      (g) => [g.key, readList(searchParams, g.key)] as const,
    );
    return Object.fromEntries(entries) as Record<FilterKey, string[]>;
  }, [searchParams]);

  const postedRaw = Number(searchParams.get(PARAM.posted));
  const posted =
    Number.isInteger(postedRaw) && postedRaw > 0 && postedRaw <= 365
      ? postedRaw
      : null;

  const sortRaw = searchParams.get(PARAM.sort);
  const sort: SortValue = sortRaw === "relevance" && q ? "relevance" : "recent";

  const viewRaw = searchParams.get(PARAM.view);
  const view: PanelMode =
    viewRaw === "companies" || viewRaw === "jobs"
      ? viewRaw
      : city && !q
        ? "companies"
        : "jobs";

  const update = useCallback(
    (mutate: (next: URLSearchParams) => void, { push = false } = {}) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          mutate(next);
          return next;
        },
        { replace: !push },
      );
    },
    [setSearchParams],
  );

  const setQuery = useCallback(
    (value: string) => {
      update((next) => {
        const trimmed = value.trim().slice(0, MAX_QUERY_LENGTH);
        if (trimmed) {
          next.set(PARAM.q, trimmed);
          next.set(PARAM.view, "jobs");
        } else {
          next.delete(PARAM.q);
          next.delete(PARAM.sort);
        }
        next.delete(PARAM.job);
        next.delete(PARAM.company);
      });
    },
    [update],
  );

  const setCity = useCallback(
    (value: string | null) => {
      update(
        (next) => {
          if (value) next.set(PARAM.city, value);
          else next.delete(PARAM.city);
          next.delete(PARAM.country);
          next.delete(PARAM.job);
          next.delete(PARAM.company);
        },
        { push: true },
      );
    },
    [update],
  );

  const setCountry = useCallback(
    (value: string | null) => {
      update(
        (next) => {
          if (value) next.set(PARAM.country, value.toUpperCase());
          else next.delete(PARAM.country);
          next.delete(PARAM.city);
          next.delete(PARAM.job);
          next.delete(PARAM.company);
        },
        { push: true },
      );
    },
    [update],
  );

  const toggle = useCallback(
    (key: FilterKey, value: string) => {
      update((next) => {
        const current = readList(next, key);
        const remaining = current.filter((v) => v !== value);
        next.delete(key);
        const updated =
          remaining.length === current.length
            ? [...current, value].slice(0, MAX_VALUES_PER_GROUP)
            : remaining;
        for (const v of updated) next.append(key, v);
        next.delete(PARAM.job);
      });
    },
    [update],
  );

  const setPosted = useCallback(
    (days: number | null) => {
      update((next) => {
        if (days) next.set(PARAM.posted, String(days));
        else next.delete(PARAM.posted);
        next.delete(PARAM.job);
      });
    },
    [update],
  );

  const setSort = useCallback(
    (value: SortValue) => {
      update((next) => {
        if (value === "recent") next.delete(PARAM.sort);
        else next.set(PARAM.sort, value);
      });
    },
    [update],
  );

  const setView = useCallback(
    (value: PanelMode) => {
      update((next) => {
        next.set(PARAM.view, value);
        next.delete(PARAM.job);
        next.delete(PARAM.company);
      });
    },
    [update],
  );

  const setJobId = useCallback(
    (value: string | null) => {
      update(
        (next) => {
          if (value) next.set(PARAM.job, value);
          else next.delete(PARAM.job);
        },
        { push: true },
      );
    },
    [update],
  );

  const setCompanySlug = useCallback(
    (value: string | null) => {
      update(
        (next) => {
          if (value) next.set(PARAM.company, value);
          else {
            next.delete(PARAM.company);
            next.delete(PARAM.job);
          }
        },
        { push: true },
      );
    },
    [update],
  );

  const clearGroup = useCallback(
    (key: FilterKey) => {
      update((next) => {
        next.delete(key);
        next.delete(PARAM.job);
      });
    },
    [update],
  );

  const clearAll = useCallback(() => {
    update((next) => {
      for (const group of FILTER_GROUPS) next.delete(group.key);
      next.delete(PARAM.posted);
    });
  }, [update]);

  const activeCount = useMemo(
    () =>
      FILTER_GROUPS.reduce((sum, g) => sum + selections[g.key].length, 0) +
      (posted ? 1 : 0),
    [selections, posted],
  );

  const chips: FilterChip[] = useMemo(() => {
    const out: FilterChip[] = [];
    for (const group of FILTER_GROUPS) {
      for (const value of selections[group.key]) {
        out.push({
          id: `${group.key}:${value}`,
          group: group.title,
          label: labelFor(group.key, value),
          remove: () => toggle(group.key, value),
        });
      }
    }
    if (posted) {
      out.push({
        id: "posted",
        group: "Posted",
        label: postedLabel(posted) ?? `Past ${posted}d`,
        remove: () => setPosted(null),
      });
    }
    return out;
  }, [selections, posted, toggle, setPosted]);

  const jobParams: ApiParams = useMemo(() => {
    const params: ApiParams = {};
    if (q) params.q = q;
    if (city) params.city = city;
    else if (country) params.country_code = country;
    for (const group of FILTER_GROUPS) {
      const values = selections[group.key];
      if (values.length) params[group.param] = values;
    }
    if (posted) params.posted_within = String(posted);
    return params;
  }, [q, city, country, selections, posted]);

  return {
    q,
    city,
    country,
    jobId,
    companySlug,
    selections,
    posted,
    sort,
    view,
    activeCount,
    chips,
    jobParams,
    setQuery,
    setCity,
    setCountry,
    toggle,
    clearGroup,
    setPosted,
    setSort,
    setView,
    setJobId,
    setCompanySlug,
    clearAll,
  };
}

export type JobFiltersApi = ReturnType<typeof useJobFilters>;
