import {
  fetchCompanies,
  fetchCompanyDetail,
  fetchCompanyJobs,
} from "@/api/companies";
import { fetchJobDetail, fetchJobs } from "@/api/jobs";
import { fetchMapCities, fetchMapCompanies } from "@/api/map";
import { GitHubIcon } from "@/components/ui/social-icons";
import {
  CARTO_KEY,
  GITHUB_REPO,
  HOME_CENTER,
  HOME_ZOOM,
  MAP_MAX_ZOOM,
  MAP_MIN_ZOOM,
} from "@/lib/constants";
import type {
  ApiParams,
  CityPin,
  CompanyDetail,
  CompanyJobsData,
  CompanyListItem,
  Job,
  JobDetail,
  PanelView,
} from "@/types";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { ArrowLeft, ChevronDown, Home, Minus, Plus, Star } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ActiveFilters } from "./components/ActiveFilters";
import { FilterPanel } from "./components/FilterPanel";
import { ResultsPanel } from "./components/ResultsPanel";
import { SearchBar } from "./components/SearchBar";
import { useDebounced } from "./hooks/useDebounced";
import { useFacets } from "./hooks/useFacets";
import { useJobFilters } from "./hooks/useJobFilters";
import { useStatusBar } from "./hooks/useStatusBar";
import { renderCompanyPins } from "./mapUtils";

const PAGE_SIZE = 20;
const COMPANY_PAGE_SIZE = 50;
const SEARCH_DEBOUNCE_MS = 250;
const FILTER_SETTLE_MS = 200;
const MIN_QUERY_LENGTH = 2;

export default function MapPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const companyLayerRef = useRef<L.LayerGroup | null>(null);

  const listAbortRef = useRef<AbortController | null>(null);
  const jobDetailAbortRef = useRef<AbortController | null>(null);
  const companyDetailAbortRef = useRef<AbortController | null>(null);
  const pendingGeoRef = useRef<{ lat: number; lng: number } | null>(null);
  const cityPinsRef = useRef<CityPin[]>([]);
  const selectCityRef = useRef<(name: string) => void>(() => {});
  const firstGeoRef = useRef(true);
  const listRequestRef = useRef(0);

  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const committedQueryRef = useRef("");
  const filterRef = useRef<HTMLDivElement>(null);
  const filterRefMobile = useRef<HTMLDivElement>(null);
  const statsPillRef = useRef<HTMLDivElement>(null);

  const { connected, stars, stats } = useStatusBar();
  const filters = useJobFilters();
  const {
    q,
    city,
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
    setJobId,
    setCompanySlug,
    setView,
    setSort,
    setPosted,
    toggle,
    clearGroup,
    clearAll,
  } = filters;

  const [filterOpen, setFilterOpen] = useState(false);
  const [draftQuery, setDraftQuery] = useState(q);
  const [panelOpen, setPanelOpen] = useState(true);
  const [showGeoHint, setShowGeoHint] = useState(false);
  const [statsOpen, setStatsOpen] = useState(false);
  const [mapReady, setMapReady] = useState(false);

  const [cityPins, setCityPins] = useState<CityPin[]>([]);
  const [mapBounds, setMapBounds] = useState<{
    lat_min: number;
    lat_max: number;
    lng_min: number;
    lng_max: number;
  } | null>(null);
  const [zoom, setZoom] = useState(HOME_ZOOM);
  const [mapCenter, setMapCenter] = useState<{
    lat: number;
    lng: number;
  } | null>(null);

  const [companies, setCompanies] = useState<CompanyListItem[]>([]);
  const [companiesLoading, setCompaniesLoading] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<CompanyDetail | null>(
    null,
  );
  const [selectedCompanyLoading, setSelectedCompanyLoading] = useState(false);
  const [selectedCompanyFailed, setSelectedCompanyFailed] = useState(false);

  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [resultTotal, setResultTotal] = useState<number | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  const [jobDetail, setJobDetail] = useState<JobDetail | null>(null);
  const [jobDetailLoading, setJobDetailLoading] = useState(false);
  const [jobDetailFailed, setJobDetailFailed] = useState(false);

  const isConnected = connected === true;
  const isChecking = connected === null;

  const settledParamsKey = useDebounced(
    JSON.stringify(jobParams),
    FILTER_SETTLE_MS,
  );
  const settledBounds = useDebounced(mapBounds, FILTER_SETTLE_MS);
  const settledParams = useMemo(
    () => JSON.parse(settledParamsKey) as ApiParams,
    [settledParamsKey],
  );

  const hasCriteria = Boolean(city || q || activeCount > 0);

  const panelView: PanelView = useMemo(() => {
    if (jobId) return "job-detail";
    if (companySlug) return "company-detail";
    if (!hasCriteria) return "default";
    return view === "companies" ? "companies" : "jobs";
  }, [jobId, companySlug, hasCriteria, view]);

  const { facets, loading: facetsLoading } = useFacets(
    settledParams,
    filterOpen,
  );

  const activePillCity = useMemo(() => {
    if (!mapCenter || cityPins.length === 0) return null;
    let best = cityPins[0];
    let bestDist = Infinity;
    for (const p of cityPins) {
      const d =
        (p.latitude - mapCenter.lat) ** 2 + (p.longitude - mapCenter.lng) ** 2;
      if (d < bestDist) {
        bestDist = d;
        best = p;
      }
    }
    return best;
  }, [mapCenter, cityPins]);

  useEffect(() => {
    if (q !== committedQueryRef.current) {
      committedQueryRef.current = q;
      setDraftQuery(q);
    }
  }, [q]);

  useEffect(() => {
    if (!filterOpen) return;
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as Node;
      const insideDesktop = filterRef.current?.contains(target) ?? false;
      const insideMobile = filterRefMobile.current?.contains(target) ?? false;
      if (!insideDesktop && !insideMobile) setFilterOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [filterOpen]);

  useEffect(() => {
    if (!statsOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (
        statsPillRef.current &&
        !statsPillRef.current.contains(e.target as Node)
      ) {
        setStatsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [statsOpen]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: HOME_CENTER,
      zoom: HOME_ZOOM,
      minZoom: MAP_MIN_ZOOM,
      zoomSnap: 0.1,
      zoomControl: false,
      wheelPxPerZoomLevel: 40,
      maxBounds: [
        [-85, -Infinity],
        [85, Infinity],
      ],
      maxBoundsViscosity: 1.0,
    });

    L.tileLayer(
      `https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png${
        CARTO_KEY ? `?key=${CARTO_KEY}` : ""
      }`,
      {
        maxZoom: MAP_MAX_ZOOM,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
      },
    ).addTo(map);

    map.on("zoomend moveend", () => {
      setZoom(map.getZoom());
      const c = map.getCenter();
      setMapCenter({ lat: c.lat, lng: c.lng });
      const b = map.getBounds();
      setMapBounds({
        lat_min: b.getSouth(),
        lat_max: b.getNorth(),
        lng_min: b.getWest(),
        lng_max: b.getEast(),
      });
    });

    mapRef.current = map;
    setMapReady(true);

    return () => {
      map.remove();
      mapRef.current = null;
      setMapReady(false);
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    const b = map.getBounds();
    setMapBounds({
      lat_min: b.getSouth(),
      lat_max: b.getNorth(),
      lng_min: b.getWest(),
      lng_max: b.getEast(),
    });
  }, [mapReady]);

  useEffect(() => {
    const ac = new AbortController();
    fetchMapCities(settledParams, ac.signal)
      .then((d) => setCityPins(d.cities))
      .catch(() => {});
    return () => ac.abort();
  }, [settledParams]);

  useEffect(() => {
    cityPinsRef.current = cityPins;
  }, [cityPins]);

  useEffect(() => {
    if (cityPins.length === 0 || !pendingGeoRef.current) return;
    const { lat, lng } = pendingGeoRef.current;
    pendingGeoRef.current = null;
    let best = cityPins[0];
    let bestDist = Infinity;
    for (const p of cityPins) {
      const d = (p.latitude - lat) ** 2 + (p.longitude - lng) ** 2;
      if (d < bestDist) {
        bestDist = d;
        best = p;
      }
    }
    selectCityRef.current(best.name);
    if (firstGeoRef.current) {
      firstGeoRef.current = false;
      setPanelOpen(false);
      setShowGeoHint(true);
    }
  }, [cityPins]);

  const handleCompanyClick = useCallback(
    (slug: string) => {
      setCompanySlug(slug);
      setPanelOpen(true);
      setShowGeoHint(false);
    },
    [setCompanySlug],
  );

  useEffect(() => {
    const map = mapRef.current;
    if (!settledBounds || !map) {
      companyLayerRef.current?.clearLayers();
      return;
    }

    const ac = new AbortController();
    fetchMapCompanies(
      {
        ...settledParams,
        lat_min: settledBounds.lat_min.toString(),
        lat_max: settledBounds.lat_max.toString(),
        lng_min: settledBounds.lng_min.toString(),
        lng_max: settledBounds.lng_max.toString(),
      },
      ac.signal,
    )
      .then((d) => {
        if (!mapRef.current) return;
        renderCompanyPins(
          mapRef.current,
          companyLayerRef,
          d.companies,
          handleCompanyClick,
        );
      })
      .catch(() => {});

    return () => ac.abort();
  }, [settledBounds, settledParams, handleCompanyClick]);

  useEffect(() => {
    if (companySlug) return;
    if (!hasCriteria) {
      setJobs([]);
      setCompanies([]);
      setResultTotal(null);
      setNextCursor(null);
      return;
    }

    listAbortRef.current?.abort();
    const ac = new AbortController();
    listAbortRef.current = ac;
    const requestId = ++listRequestRef.current;

    if (view === "companies") {
      setCompaniesLoading(true);
      fetchCompanies(
        { ...settledParams, limit: String(COMPANY_PAGE_SIZE) },
        ac.signal,
      )
        .then((d) => {
          if (requestId !== listRequestRef.current) return;
          setCompanies(d.companies);
          setResultTotal(d.total);
          setNextCursor(null);
        })
        .catch(() => {})
        .finally(() => {
          if (!ac.signal.aborted) setCompaniesLoading(false);
        });
      return () => ac.abort();
    }

    setJobsLoading(true);
    fetchJobs({ ...settledParams, sort, limit: String(PAGE_SIZE) }, ac.signal)
      .then((d) => {
        if (requestId !== listRequestRef.current) return;
        setJobs(d.jobs);
        setResultTotal(d.total);
        setNextCursor(d.next_cursor ?? null);
      })
      .catch(() => {})
      .finally(() => {
        if (!ac.signal.aborted) setJobsLoading(false);
      });

    return () => ac.abort();
  }, [settledParams, view, sort, companySlug, hasCriteria]);

  useEffect(() => {
    if (!companySlug) {
      setSelectedCompany(null);
      return;
    }

    companyDetailAbortRef.current?.abort();
    const ac = new AbortController();
    companyDetailAbortRef.current = ac;
    const requestId = ++listRequestRef.current;

    setSelectedCompanyLoading(true);
    setSelectedCompanyFailed(false);
    setJobs([]);
    setNextCursor(null);

    Promise.all([
      fetchCompanyDetail(companySlug, ac.signal),
      fetchCompanyJobs(
        companySlug,
        { ...settledParams, limit: String(PAGE_SIZE) },
        ac.signal,
      ),
    ])
      .then(([detail, jobsData]: [CompanyDetail, CompanyJobsData]) => {
        if (requestId !== listRequestRef.current) return;
        setSelectedCompany(detail);
        setJobs(jobsData.jobs);
        setResultTotal(jobsData.total);
        const map = mapRef.current;
        if (map && !city && detail.latitude && detail.longitude) {
          map.flyTo([detail.latitude, detail.longitude], 10, { duration: 1.2 });
        }
      })
      .catch(() => {
        if (!ac.signal.aborted) setSelectedCompanyFailed(true);
      })
      .finally(() => {
        if (!ac.signal.aborted) setSelectedCompanyLoading(false);
      });

    return () => ac.abort();
  }, [companySlug, settledParams, city]);

  useEffect(() => {
    if (!jobId) {
      setJobDetail(null);
      return;
    }

    jobDetailAbortRef.current?.abort();
    const ac = new AbortController();
    jobDetailAbortRef.current = ac;
    setJobDetailLoading(true);
    setJobDetailFailed(false);

    fetchJobDetail(jobId, ac.signal)
      .then((d) => {
        setJobDetail(d);
        if (!city && d.latitude && d.longitude) {
          mapRef.current?.flyTo([d.latitude, d.longitude], 12, {
            duration: 1.2,
          });
        }
      })
      .catch(() => {
        if (!ac.signal.aborted) setJobDetailFailed(true);
      })
      .finally(() => {
        if (!ac.signal.aborted) setJobDetailLoading(false);
      });

    return () => ac.abort();
  }, [jobId, city]);

  const pagesByOffset = Boolean(companySlug) || sort === "relevance";
  const hasMore =
    panelView === "jobs" || panelView === "company-detail"
      ? pagesByOffset
        ? resultTotal !== null && jobs.length < resultTotal
        : Boolean(nextCursor)
      : false;

  function handleLoadMore() {
    if (loadingMore) return;
    setLoadingMore(true);
    const requestId = listRequestRef.current;

    const request = companySlug
      ? fetchCompanyJobs(companySlug, {
          ...settledParams,
          limit: String(PAGE_SIZE),
          offset: String(jobs.length),
        }).then((d: CompanyJobsData) => ({
          jobs: d.jobs,
          next_cursor: null as string | null,
        }))
      : fetchJobs({
          ...settledParams,
          sort,
          limit: String(PAGE_SIZE),
          ...(nextCursor
            ? { cursor: nextCursor }
            : { offset: String(jobs.length) }),
        });

    request
      .then((d) => {
        if (requestId !== listRequestRef.current) return;
        setJobs((prev) => [...prev, ...d.jobs]);
        setNextCursor(d.next_cursor ?? null);
      })
      .catch(() => {})
      .finally(() => setLoadingMore(false));
  }

  const commitQuery = useCallback(
    (value: string) => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
      const trimmed = value.trim();
      const effective = trimmed.length < MIN_QUERY_LENGTH ? "" : trimmed;
      committedQueryRef.current = effective;
      setQuery(effective);
      setPanelOpen(true);
      setShowGeoHint(false);
    },
    [setQuery],
  );

  function handleQueryChange(value: string) {
    setDraftQuery(value);
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(
      () => commitQuery(value),
      SEARCH_DEBOUNCE_MS,
    );
  }

  function handleClearQuery() {
    setDraftQuery("");
    commitQuery("");
  }

  const selectCity = useCallback(
    (cityName: string) => {
      setCity(cityName);
      setPanelOpen(true);
      setShowGeoHint(false);
    },
    [setCity],
  );

  useEffect(() => {
    selectCityRef.current = selectCity;
  }, [selectCity]);

  function handleBackToList() {
    if (panelView === "job-detail") setJobId(null);
    else if (panelView === "company-detail") setCompanySlug(null);
  }

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !navigator.geolocation) return;
    if (city || q || activeCount > 0) return;

    let disposed = false;
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        if (disposed) return;
        map.flyTo([coords.latitude, coords.longitude], 12, { duration: 1.6 });
        const pins = cityPinsRef.current;
        if (pins.length > 0) {
          let best = pins[0];
          let bestDist = Infinity;
          for (const p of pins) {
            const d =
              (p.latitude - coords.latitude) ** 2 +
              (p.longitude - coords.longitude) ** 2;
            if (d < bestDist) {
              bestDist = d;
              best = p;
            }
          }
          selectCityRef.current(best.name);
          if (firstGeoRef.current) {
            firstGeoRef.current = false;
            setPanelOpen(false);
            setShowGeoHint(true);
          }
        } else {
          pendingGeoRef.current = {
            lat: coords.latitude,
            lng: coords.longitude,
          };
        }
      },
      () => {},
      { enableHighAccuracy: true, timeout: 10000 },
    );
    return () => {
      disposed = true;
    };
  }, [mapReady]);

  const filterPanel = (
    <FilterPanel
      selections={selections}
      posted={posted}
      facets={facets}
      facetsLoading={facetsLoading}
      activeCount={activeCount}
      onToggle={toggle}
      onClearGroup={clearGroup}
      onPostedChange={setPosted}
      onClearAll={clearAll}
      onClose={() => setFilterOpen(false)}
    />
  );

  return (
    <div className="flex h-screen flex-col gap-3 bg-gray-50 p-5 font-sans antialiased">
      <header className="relative flex shrink-0 items-center">
        <Link
          to="/"
          className="shrink-0 text-4xl font-semibold tracking-tight text-gray-900"
        >
          jobdex
        </Link>

        <div className="pointer-events-none absolute inset-0 hidden items-center justify-center md:flex">
          <div className="pointer-events-auto flex items-center gap-2">
            <Link
              to="/"
              aria-label="Back"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-gray-500 transition-colors hover:bg-black/5"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            </Link>

            <div ref={filterRef} className="relative w-96">
              <SearchBar
                value={draftQuery}
                onChange={handleQueryChange}
                onSubmit={commitQuery}
                onClear={handleClearQuery}
                filterOpen={filterOpen}
                onToggleFilters={() => setFilterOpen((o) => !o)}
                activeCount={activeCount}
              >
                {filterOpen && (
                  <div className="absolute top-full left-0 z-[9999] mt-2 w-full">
                    {filterPanel}
                  </div>
                )}
              </SearchBar>
            </div>
          </div>
        </div>

        <nav
          aria-label="Status"
          className="ml-auto inline-flex shrink-0 items-center gap-2 rounded-full border border-black/10 bg-white/90 px-2.5 py-1.5 shadow-sm shadow-black/5 backdrop-blur-md"
        >
          <div className="flex items-center gap-1.5 px-1.5 py-0.5">
            <span
              className={`relative flex h-2 w-2 shrink-0 ${isChecking ? "opacity-40" : ""}`}
              aria-hidden="true"
            >
              <span
                className={`inline-flex h-2 w-2 rounded-full ${
                  isConnected
                    ? "dot-pulse-green bg-emerald-500"
                    : "dot-pulse-red bg-red-500"
                }`}
              />
            </span>
            <span className="hidden text-xs font-medium text-gray-600 sm:inline">
              {isChecking
                ? "Checking"
                : isConnected
                  ? "Connected"
                  : "Disconnected"}
            </span>
          </div>

          <div className="h-4 w-px bg-black/10" aria-hidden="true" />

          <a
            href={`https://github.com/${GITHUB_REPO}`}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`View on GitHub${stars !== null ? ` · ${stars} stars` : ""}`}
            className="flex h-8 items-center gap-1.5 rounded-full px-2 text-xs font-medium text-gray-600 transition-colors hover:bg-black hover:text-white"
          >
            <GitHubIcon className="size-3.5" />
            {stars !== null && (
              <span className="flex items-center gap-1">
                <Star
                  className="size-3 fill-gray-400 stroke-gray-400"
                  aria-hidden="true"
                />
                {stars.toLocaleString()}
              </span>
            )}
          </a>
        </nav>
      </header>

      <div className="flex shrink-0 md:hidden">
        <div ref={filterRefMobile} className="relative w-full">
          <SearchBar
            value={draftQuery}
            onChange={handleQueryChange}
            onSubmit={commitQuery}
            onClear={handleClearQuery}
            filterOpen={filterOpen}
            onToggleFilters={() => setFilterOpen((o) => !o)}
            activeCount={activeCount}
          >
            {filterOpen && (
              <div className="absolute top-full left-0 z-[9999] mt-2 w-full">
                {filterPanel}
              </div>
            )}
          </SearchBar>
        </div>
      </div>

      <ActiveFilters
        city={city}
        onClearCity={() => setCity(null)}
        chips={chips}
        onClearAll={clearAll}
      />

      <div className="flex flex-1 overflow-hidden">
        <div className="relative flex-1 overflow-hidden rounded-2xl border border-black/10 shadow-lg shadow-black/8">
          <div
            ref={containerRef}
            className="absolute inset-0"
            aria-label="Interactive world map"
          />

          <div
            ref={statsPillRef}
            className="absolute top-4 left-4 z-[1000] inline-block"
          >
            <button
              onClick={() => stats && setStatsOpen((o) => !o)}
              aria-expanded={statsOpen}
              className={`flex items-center gap-1.5 overflow-hidden rounded-full border border-white/20 bg-white/25 px-3 py-1.5 shadow-sm shadow-black/5 backdrop-blur-md ${
                stats ? "transition-colors hover:bg-white/40" : "cursor-default"
              }`}
            >
              <span className="text-[10px] leading-none font-medium text-gray-700">
                {(stats?.active_jobs ?? 0).toLocaleString()} jobs &middot;{" "}
                {(stats?.cities_with_jobs ?? 0).toLocaleString()} cities indexed
              </span>
              {stats && (
                <ChevronDown
                  className={`h-2.5 w-2.5 text-gray-500 transition-transform duration-200 ${statsOpen ? "rotate-180" : ""}`}
                  aria-hidden="true"
                />
              )}
            </button>

            {statsOpen && stats && (
              <div className="no-scrollbar absolute top-full left-0 mt-2 max-h-96 w-56 overflow-y-auto rounded-2xl border border-white/20 bg-white/60 shadow-lg shadow-black/8 backdrop-blur-xl">
                <div className="space-y-3 p-3">
                  <div>
                    <p className="mb-1.5 text-[9px] font-medium tracking-widest text-gray-500 uppercase">
                      Overview
                    </p>
                    <div className="space-y-1">
                      {[
                        ["Companies", stats.total_companies],
                        ["Active jobs", stats.active_jobs],
                        ["Total cities", stats.total_cities],
                        ["Cities with jobs", stats.cities_with_jobs],
                      ].map(([label, value]) => (
                        <div
                          key={label as string}
                          className="flex justify-between text-[10px]"
                        >
                          <span className="text-gray-500">{label}</span>
                          <span className="font-medium text-gray-800">
                            {(value as number).toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="h-px bg-black/5" />

                  <div>
                    <p className="mb-1.5 text-[9px] font-medium tracking-widest text-gray-500 uppercase">
                      Top Cities
                    </p>
                    <div className="space-y-1">
                      {stats.top_cities.slice(0, 5).map((c) => (
                        <button
                          key={c.city}
                          onClick={() => {
                            selectCity(c.city);
                            setStatsOpen(false);
                          }}
                          className="flex w-full justify-between rounded px-1 py-0.5 text-[10px] transition-colors hover:bg-black/5"
                        >
                          <span className="text-gray-500">{c.city}</span>
                          <span className="font-medium text-gray-800">
                            {c.job_count.toLocaleString()}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="h-px bg-black/5" />

                  <div>
                    <p className="mb-1.5 text-[9px] font-medium tracking-widest text-gray-500 uppercase">
                      Regions
                    </p>
                    <div className="space-y-1">
                      {stats.top_regions.map((r) => (
                        <div
                          key={r.region}
                          className="flex justify-between text-[10px]"
                        >
                          <span className="text-gray-500">
                            {r.region
                              .replace(/_/g, " ")
                              .replace(/\b\w/g, (c) => c.toUpperCase())}
                          </span>
                          <span className="font-medium text-gray-800">
                            {r.job_count.toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="h-px bg-black/5" />

                  <div>
                    <p className="mb-1.5 text-[9px] font-medium tracking-widest text-gray-500 uppercase">
                      Roles
                    </p>
                    <div className="space-y-1">
                      {Object.entries(stats.role_categories)
                        .sort(([, a], [, b]) => b - a)
                        .slice(0, 8)
                        .map(([role, count]) => (
                          <button
                            key={role}
                            onClick={() => {
                              toggle("role", role);
                              setStatsOpen(false);
                            }}
                            className="flex w-full justify-between rounded px-1 py-0.5 text-[10px] transition-colors hover:bg-black/5"
                          >
                            <span className="text-gray-500 capitalize">
                              {role}
                            </span>
                            <span className="font-medium text-gray-800">
                              {count.toLocaleString()}
                            </span>
                          </button>
                        ))}
                    </div>
                  </div>

                  <div className="h-px bg-black/5" />

                  <div>
                    <p className="mb-1.5 text-[9px] font-medium tracking-widest text-gray-500 uppercase">
                      Sources
                    </p>
                    <div className="space-y-1">
                      {Object.entries(stats.ats_breakdown)
                        .sort(([, a], [, b]) => b - a)
                        .map(([ats, count]) => (
                          <button
                            key={ats}
                            onClick={() => {
                              toggle("source", ats);
                              setStatsOpen(false);
                            }}
                            className="flex w-full justify-between rounded px-1 py-0.5 text-[10px] transition-colors hover:bg-black/5"
                          >
                            <span className="text-gray-500 capitalize">
                              {ats === "ycombinator"
                                ? "Y Combinator"
                                : ats.charAt(0).toUpperCase() + ats.slice(1)}
                            </span>
                            <span className="font-medium text-gray-800">
                              {count.toLocaleString()}
                            </span>
                          </button>
                        ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {zoom >= 10 && (
            <div className="absolute top-4 right-4 z-[1000] flex items-center overflow-hidden rounded-full border border-white/20 bg-white/25 px-3 py-1.5 shadow-sm shadow-black/5 backdrop-blur-md sm:right-auto sm:left-1/2 sm:-translate-x-1/2">
              <span className="text-[10px] leading-none font-medium text-gray-700">
                {(activePillCity?.company_count ?? 0).toLocaleString()}{" "}
                companies &middot;{" "}
                {(activePillCity?.job_count ?? 0).toLocaleString()} jobs
              </span>
            </div>
          )}

          <div className="absolute bottom-4 left-4 z-[1000] hidden flex-col overflow-hidden rounded-full border border-white/20 bg-white/25 shadow-sm shadow-black/5 backdrop-blur-md sm:flex">
            <button
              aria-label="Zoom in"
              onClick={() => mapRef.current?.zoomIn()}
              className="flex h-9 w-9 items-center justify-center text-gray-700 transition-colors hover:bg-white/50"
            >
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
            <div className="h-px w-full bg-black/10" />
            <span className="flex h-7 w-9 items-center justify-center text-[10px] font-medium text-gray-600">
              {Math.round((zoom / MAP_MAX_ZOOM) * 100)}%
            </span>
            <div className="h-px w-full bg-black/10" />
            <button
              aria-label="Zoom out"
              onClick={() => mapRef.current?.zoomOut()}
              disabled={zoom <= MAP_MIN_ZOOM}
              className="flex h-9 w-9 items-center justify-center text-gray-700 transition-colors hover:bg-white/50 disabled:cursor-not-allowed disabled:opacity-30"
            >
              <Minus className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
            <div className="h-px w-full bg-black/10" />
            <button
              aria-label="World overview"
              onClick={() =>
                mapRef.current?.flyTo(HOME_CENTER, HOME_ZOOM, { duration: 1.2 })
              }
              className="flex h-9 w-9 items-center justify-center text-gray-700 transition-colors hover:bg-white/50"
            >
              <Home className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>

          <ResultsPanel
            open={panelOpen}
            onToggle={() => {
              setPanelOpen((o) => !o);
              if (showGeoHint) setShowGeoHint(false);
            }}
            showHint={showGeoHint}
            view={panelView}
            mode={view}
            onModeChange={setView}
            selectedCity={city}
            total={resultTotal}
            sort={sort}
            onSortChange={setSort}
            hasQuery={Boolean(q)}
            hasFilters={activeCount > 0}
            onClearFilters={clearAll}
            onSearchEverywhere={() => setCity(null)}
            companies={companies}
            companiesLoading={companiesLoading}
            onCompanyClick={handleCompanyClick}
            selectedCompany={selectedCompany}
            selectedCompanyLoading={selectedCompanyLoading}
            selectedCompanyFailed={selectedCompanyFailed}
            jobs={jobs}
            jobsLoading={jobsLoading}
            hasMore={hasMore}
            loadingMore={loadingMore}
            onLoadMore={handleLoadMore}
            onJobClick={setJobId}
            jobDetail={jobDetail}
            jobDetailLoading={jobDetailLoading}
            jobDetailFailed={jobDetailFailed}
            onBack={handleBackToList}
          />
        </div>
      </div>

      <style>{`
        .leaflet-control-attribution { font-size: 10px; }

        @keyframes pulse-green {
          0%, 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
          60%       { box-shadow: 0 0 0 5px rgba(16, 185, 129, 0); }
        }
        @keyframes pulse-red {
          0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.6); }
          60%       { box-shadow: 0 0 0 4px rgba(239, 68, 68, 0); }
        }
        .dot-pulse-green { animation: pulse-green 2.4s ease-out infinite; }
        .dot-pulse-red   { animation: pulse-red   2.4s ease-out infinite; }

        .map-tt-wrap {
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
        }
        .map-tt-wrap .leaflet-tooltip-tip { display: none !important; }
        .map-tt {
          background: rgba(17,24,39,0.92);
          backdrop-filter: blur(8px);
          border-radius: 8px;
          padding: 6px 10px;
          display: flex; flex-direction: column; gap: 2px;
          white-space: nowrap;
        }
        .map-tt strong {
          font-size: 12px; font-weight: 600; color: #f9fafb;
          font-family: var(--font-sans, system-ui, sans-serif);
        }
        .map-tt span {
          font-size: 11px; color: rgba(249,250,251,0.6);
          font-family: var(--font-sans, system-ui, sans-serif);
        }

        .company-pin {
          width: 26px; height: 26px;
          border-radius: 6px;
          border: 1.5px solid rgba(255,255,255,0.9);
          background: #fff;
          box-shadow: 0 2px 6px rgba(0,0,0,0.15);
          overflow: hidden;
          display: flex; align-items: center; justify-content: center;
          font-size: 11px; font-weight: 600;
          cursor: pointer;
        }
        .company-pin img {
          width: 100%; height: 100%; object-fit: contain;
        }
      `}</style>
    </div>
  );
}
