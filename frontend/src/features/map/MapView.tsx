import { GitHubIcon } from "@/components/ui/social-icons";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  ArrowLeft,
  Home,
  Minus,
  Plus,
  Search,
  SlidersHorizontal,
  Star,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { FilterDropdown } from "./components/FilterDropdown";
import { ResultsPanel } from "./components/ResultsPanel";
import {
  API_BASE,
  GITHUB_REPO,
  HOME_CENTER,
  HOME_ZOOM,
  MAP_MAX_ZOOM,
} from "./constants";
import type {
  CityPin,
  CompanyDetail,
  CompanyListItem,
  CompanyPin,
  Job,
  JobDetail,
  PanelView,
} from "./types";
import { escapeHtml } from "./utils";

export function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  const companyLayerRef = useRef<L.LayerGroup | null>(null);

  const jobsAbortRef = useRef<AbortController | null>(null);
  const jobDetailAbortRef = useRef<AbortController | null>(null);
  const companiesAbortRef = useRef<AbortController | null>(null);
  const companyDetailAbortRef = useRef<AbortController | null>(null);
  const pendingGeoRef = useRef<{ lat: number; lng: number } | null>(null);
  const cityPinsRef = useRef<CityPin[]>([]);
  const handleCityClickRef = useRef<(name: string) => void>(() => {});

  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const filterRef = useRef<HTMLDivElement>(null);
  const filterRefMobile = useRef<HTMLDivElement>(null);

  const [connected, setConnected] = useState<boolean | null>(null);
  const [stars, setStars] = useState<number | null>(null);
  const [indexedStats, setIndexedStats] = useState<{
    jobs: number;
    cities: number;
  } | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const [filterOpen, setFilterOpen] = useState(false);

  useEffect(() => {
    if (!filterOpen) return;
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as Node;
      const insideDesktop = filterRef.current?.contains(target) ?? false;
      const insideMobile = filterRefMobile.current?.contains(target) ?? false;
      if (!insideDesktop && !insideMobile) {
        setFilterOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [filterOpen]);

  const [mapReady, setMapReady] = useState(false);

  const [roleFilter, setRoleFilter] = useState<string | null>(null);
  const [remoteFilter, setRemoteFilter] = useState<boolean | null>(null);

  const [query, setQuery] = useState("");
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

  const [panelView, setPanelView] = useState<PanelView>("default");
  const [selectedCity, setSelectedCity] = useState<string | null>(null);

  const [companies, setCompanies] = useState<CompanyListItem[]>([]);
  const [companiesLoading, setCompaniesLoading] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<CompanyDetail | null>(
    null,
  );
  const [selectedCompanyLoading, setSelectedCompanyLoading] = useState(false);

  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  const [jobDetail, setJobDetail] = useState<JobDetail | null>(null);
  const [jobDetailLoading, setJobDetailLoading] = useState(false);

  const isConnected = connected === true;
  const isChecking = connected === null;
  const hasActiveFilter = roleFilter !== null || remoteFilter !== null;
  const activePillCity = (() => {
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
  })();

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
      .then((r) => r.json())
      .then((d) => {
        if (
          typeof d.active_jobs === "number" &&
          typeof d.cities_with_jobs === "number"
        ) {
          setIndexedStats({ jobs: d.active_jobs, cities: d.cities_with_jobs });
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: HOME_CENTER,
      zoom: HOME_ZOOM,
      zoomSnap: 0.1,
      zoomControl: false,
    });

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
      {
        maxZoom: MAP_MAX_ZOOM,
        subdomains: "abcd",
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
    const params = new URLSearchParams();
    if (roleFilter) params.set("role", roleFilter);
    if (remoteFilter !== null) params.set("is_remote", String(remoteFilter));
    const qs = params.toString();

    fetch(`${API_BASE}/map/cities${qs ? `?${qs}` : ""}`, { signal: ac.signal })
      .then((r) => r.json())
      .then((d) => {
        if (d.cities) setCityPins(d.cities);
      })
      .catch(() => {});

    return () => ac.abort();
  }, [roleFilter, remoteFilter]);

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
    handleCityClickRef.current(best.name);
  }, [cityPins]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapBounds || !map) {
      companyLayerRef.current?.clearLayers();
      return;
    }

    const ac = new AbortController();
    const params = new URLSearchParams({
      lat_min: mapBounds.lat_min.toString(),
      lat_max: mapBounds.lat_max.toString(),
      lng_min: mapBounds.lng_min.toString(),
      lng_max: mapBounds.lng_max.toString(),
    });
    if (roleFilter) params.set("role", roleFilter);
    if (remoteFilter !== null) params.set("is_remote", String(remoteFilter));

    fetch(`${API_BASE}/map/companies?${params}`, { signal: ac.signal })
      .then((r) => r.json())
      .then((d: { companies?: CompanyPin[] }) => {
        if (!d.companies || !mapRef.current) return;
        renderCompanyPins(mapRef.current, d.companies, handleCompanyClick);
      })
      .catch(() => {});

    return () => ac.abort();
  }, [mapBounds, roleFilter, remoteFilter]);

  useEffect(() => {
    if (panelView === "companies" && selectedCity) {
      handleCityClick(selectedCity);
    } else if (panelView === "jobs" && selectedCity) {
      loadJobs(selectedCity, null, true);
    }
  }, [roleFilter, remoteFilter]);

  function renderCompanyPins(
    map: L.Map,
    companies: CompanyPin[],
    onCompanyClick: (slug: string) => void,
  ) {
    if (!companyLayerRef.current) {
      companyLayerRef.current = L.layerGroup().addTo(map);
    } else {
      companyLayerRef.current.clearLayers();
    }

    const byCoord = new Map<string, CompanyPin[]>();
    for (const co of companies.slice(0, 200)) {
      if (co.latitude == null || co.longitude == null) continue;
      const key = `${co.latitude.toFixed(3)},${co.longitude.toFixed(3)}`;
      const arr = byCoord.get(key) ?? [];
      arr.push(co);
      byCoord.set(key, arr);
    }

    for (const group of byCoord.values()) {
      group.forEach((co, idx) => {
        let lat = co.latitude!;
        let lng = co.longitude!;

        if (group.length > 1) {
          const angle = (idx / group.length) * 2 * Math.PI - Math.PI / 2;
          const ring = Math.floor(idx / 8);
          const radius = 0.007 + ring * 0.006;
          lat += Math.sin(angle) * radius;
          lng += Math.cos(angle) * radius;
        }

        const wrap = document.createElement("div");
        wrap.className = "company-pin";

        if (co.logo_url) {
          const img = document.createElement("img");
          img.alt = "";
          img.style.cssText = "width:100%;height:100%;object-fit:contain;";
          img.onerror = () => {
            wrap.innerHTML = co.name.charAt(0).toUpperCase();
          };
          img.src = co.logo_url;
          wrap.appendChild(img);
        } else {
          wrap.textContent = co.name.charAt(0).toUpperCase();
        }

        const icon = L.divIcon({
          className: "",
          html: wrap as unknown as string,
          iconSize: [26, 26],
          iconAnchor: [13, 13],
        });

        const marker = L.marker([lat, lng], { icon });
        marker.bindTooltip(
          `<div class="map-tt"><strong>${escapeHtml(co.name)}</strong><span>${co.job_count} open roles</span></div>`,
          { direction: "top", offset: [0, -8], className: "map-tt-wrap" },
        );
        marker.on("click", () => onCompanyClick(co.slug));
        companyLayerRef.current?.addLayer(marker);
      });
    }
  }

  const loadJobs = useCallback(
    async (city: string | null, cursor: string | null, replace: boolean) => {
      jobsAbortRef.current?.abort();
      const ac = new AbortController();
      jobsAbortRef.current = ac;

      replace ? setJobsLoading(true) : setLoadingMore(true);

      try {
        const params = new URLSearchParams({ limit: "20" });
        if (city) params.set("city", city);
        if (cursor) params.set("cursor", cursor);
        if (roleFilter) params.set("role_category", roleFilter);
        if (remoteFilter !== null)
          params.set("is_remote", String(remoteFilter));

        const r = await fetch(`${API_BASE}/jobs?${params}`, {
          signal: ac.signal,
        });
        const d = await r.json();

        if (d.jobs) {
          setJobs((prev) => (replace ? d.jobs : [...prev, ...d.jobs]));
          setNextCursor(d.next_cursor ?? null);
        }
      } catch {
      } finally {
        setJobsLoading(false);
        setLoadingMore(false);
      }
    },
    [roleFilter, remoteFilter],
  );

  const handleCityClick = useCallback(
    (cityName: string) => {
      setSelectedCity(cityName);
      setSelectedCompany(null);
      setJobDetail(null);
      setQuery("");
      setPanelOpen(true);
      setPanelView("companies");
      setCompanies([]);
      setJobs([]);
      setNextCursor(null);

      companiesAbortRef.current?.abort();
      const ac = new AbortController();
      companiesAbortRef.current = ac;
      setCompaniesLoading(true);

      const params = new URLSearchParams({ city: cityName, limit: "50" });
      if (roleFilter) params.set("role_category", roleFilter);
      if (remoteFilter !== null) params.set("is_remote", String(remoteFilter));

      fetch(`${API_BASE}/companies?${params}`, { signal: ac.signal })
        .then((r) => r.json())
        .then((d) => {
          if (d.companies) setCompanies(d.companies);
        })
        .catch(() => {})
        .finally(() => setCompaniesLoading(false));
    },
    [roleFilter, remoteFilter],
  );

  const handleCompanyClick = useCallback(
    (slug: string) => {
      companyDetailAbortRef.current?.abort();
      const ac = new AbortController();
      companyDetailAbortRef.current = ac;

      setSelectedCompany(null);
      setJobDetail(null);
      setPanelView("company-detail");
      setSelectedCompanyLoading(true);
      setJobs([]);
      setNextCursor(null);

      const jobsParams = new URLSearchParams({ limit: "20" });
      if (roleFilter) jobsParams.set("role_category", roleFilter);
      if (remoteFilter !== null)
        jobsParams.set("is_remote", String(remoteFilter));

      Promise.all([
        fetch(`${API_BASE}/companies/${encodeURIComponent(slug)}`, {
          signal: ac.signal,
        }).then((r) => r.json()),
        fetch(
          `${API_BASE}/companies/${encodeURIComponent(slug)}/jobs?${jobsParams}`,
          { signal: ac.signal },
        ).then((r) => r.json()),
      ])
        .then(([detail, jobsData]) => {
          setSelectedCompany(detail as CompanyDetail);
          if (jobsData.jobs) {
            setJobs(jobsData.jobs);
            setNextCursor(
              jobsData.total > jobsData.jobs.length ? "more" : null,
            );
          }
          const map = mapRef.current;
          if (map && !selectedCity) {
            const co = detail as CompanyDetail;
            if (co.latitude && co.longitude) {
              map.flyTo([co.latitude, co.longitude], 10, { duration: 1.2 });
            }
          }
        })
        .catch(() => {})
        .finally(() => setSelectedCompanyLoading(false));
    },
    [selectedCity, roleFilter, remoteFilter],
  );

  function handleSearchSubmit(q: string) {
    if (!q.trim()) return;
    jobsAbortRef.current?.abort();
    const ac = new AbortController();
    jobsAbortRef.current = ac;
    setSelectedCity(null);
    setJobDetail(null);
    setPanelView("jobs");
    setPanelOpen(true);
    setJobsLoading(true);
    setJobs([]);
    setNextCursor(null);

    const params = new URLSearchParams({ q: q.trim(), limit: "20" });
    if (roleFilter) params.set("role_category", roleFilter);
    if (remoteFilter !== null) params.set("is_remote", String(remoteFilter));

    fetch(`${API_BASE}/jobs?${params}`, { signal: ac.signal })
      .then((r) => r.json())
      .then((d) => {
        if (d.jobs) {
          setJobs(d.jobs);
          setNextCursor(d.next_cursor ?? null);
        }
      })
      .catch(() => {})
      .finally(() => setJobsLoading(false));
  }

  function handleQueryChange(val: string) {
    setQuery(val);
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    if (!val.trim()) {
      if (selectedCity) {
        setPanelView("companies");
      } else {
        setPanelView("default");
      }
      return;
    }
    searchDebounceRef.current = setTimeout(() => handleSearchSubmit(val), 450);
  }

  function handleJobClick(jobId: string) {
    setJobDetail(null);
    setPanelView("job-detail");
    setJobDetailLoading(true);

    jobDetailAbortRef.current?.abort();
    const ac = new AbortController();
    jobDetailAbortRef.current = ac;

    fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}`, {
      signal: ac.signal,
    })
      .then((r) => r.json())
      .then((d: JobDetail) => setJobDetail(d))
      .catch(() => {})
      .finally(() => setJobDetailLoading(false));
  }

  function handleLoadMore() {
    if (selectedCompany) {
      setLoadingMore(true);
      const loadParams = new URLSearchParams({
        limit: "20",
        offset: String(jobs.length),
      });
      if (selectedCity) loadParams.set("city", selectedCity);
      if (roleFilter) loadParams.set("role_category", roleFilter);
      if (remoteFilter !== null)
        loadParams.set("is_remote", String(remoteFilter));

      fetch(
        `${API_BASE}/companies/${encodeURIComponent(selectedCompany.slug)}/jobs?${loadParams}`,
      )
        .then((r) => r.json())
        .then((d) => {
          if (d.jobs) {
            const allJobs = [...jobs, ...d.jobs];
            setJobs(allJobs);
            setNextCursor(d.total > allJobs.length ? "more" : null);
          }
        })
        .catch(() => {})
        .finally(() => setLoadingMore(false));
    } else {
      loadJobs(selectedCity, nextCursor, false);
    }
  }

  function handleBackToList() {
    if (panelView === "job-detail") {
      setJobDetail(null);
      if (selectedCompany) {
        setPanelView("company-detail");
      } else {
        setPanelView("jobs");
      }
    } else if (panelView === "company-detail") {
      setSelectedCompany(null);
      setPanelView(selectedCity ? "companies" : "default");
    }
  }

  function handleClearCity() {
    companiesAbortRef.current?.abort();
    companyDetailAbortRef.current?.abort();
    setSelectedCity(null);
    setSelectedCompany(null);
    setCompanies([]);
    setJobs([]);
    setNextCursor(null);
    setPanelView("default");
    setQuery("");
  }

  useEffect(() => {
    handleCityClickRef.current = handleCityClick;
  }, [handleCityClick]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !navigator.geolocation) return;
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
          handleCityClickRef.current(best.name);
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

            <div className="relative w-96" ref={filterRef}>
              <Search
                className="pointer-events-none absolute top-1/2 left-3.5 h-3.5 w-3.5 -translate-y-1/2 text-gray-400"
                aria-hidden="true"
              />
              <input
                type="search"
                value={query}
                onChange={(e) => handleQueryChange(e.target.value)}
                onKeyDown={(e) =>
                  e.key === "Enter" && handleSearchSubmit(query)
                }
                placeholder="Search jobs, companies, roles..."
                className="w-full rounded-full border border-black/10 bg-white py-2.5 pr-10 pl-10 text-sm text-gray-900 shadow-sm shadow-black/5 outline-none placeholder:text-gray-400 focus:border-black/20"
              />
              <button
                aria-label="Filter"
                onClick={() => setFilterOpen((o) => !o)}
                className={`absolute top-1/2 right-3 -translate-y-1/2 transition-colors ${hasActiveFilter ? "text-gray-900" : "text-gray-400 hover:text-gray-700"}`}
              >
                <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
              {filterOpen && (
                <div className="absolute top-full left-0 z-[9999] mt-2 w-full">
                  <FilterDropdown
                    roleFilter={roleFilter}
                    remoteFilter={remoteFilter}
                    onRoleChange={(v) => {
                      setRoleFilter(v);
                      setFilterOpen(false);
                    }}
                    onRemoteChange={(v) => {
                      setRemoteFilter(v);
                      setFilterOpen(false);
                    }}
                  />
                </div>
              )}
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
        <div className="relative w-full" ref={filterRefMobile}>
          <Search
            className="pointer-events-none absolute top-1/2 left-3.5 h-3.5 w-3.5 -translate-y-1/2 text-gray-400"
            aria-hidden="true"
          />
          <input
            type="search"
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearchSubmit(query)}
            placeholder="Search jobs, companies, roles..."
            className="w-full rounded-full border border-black/10 bg-white py-2.5 pr-10 pl-10 text-sm text-gray-900 shadow-sm shadow-black/5 outline-none placeholder:text-gray-400 focus:border-black/20"
          />
          <button
            aria-label="Filter"
            onClick={() => setFilterOpen((o) => !o)}
            className={`absolute top-1/2 right-3 -translate-y-1/2 transition-colors ${hasActiveFilter ? "text-gray-900" : "text-gray-400 hover:text-gray-700"}`}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
          {filterOpen && (
            <div className="absolute top-full left-0 z-[9999] mt-2 w-full">
              <FilterDropdown
                roleFilter={roleFilter}
                remoteFilter={remoteFilter}
                onRoleChange={(v) => {
                  setRoleFilter(v);
                  setFilterOpen(false);
                }}
                onRemoteChange={(v) => {
                  setRemoteFilter(v);
                  setFilterOpen(false);
                }}
              />
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="relative flex-1 overflow-hidden rounded-2xl border border-black/10 shadow-lg shadow-black/8">
          <div
            ref={containerRef}
            className="absolute inset-0"
            aria-label="Interactive world map"
          />

          {indexedStats && (
            <div className="absolute top-4 left-4 z-[1000] overflow-hidden rounded-full border border-white/20 bg-white/25 px-3 py-1.5 shadow-sm shadow-black/5 backdrop-blur-md">
              <span className="text-[10px] font-medium text-gray-700">
                {indexedStats.jobs.toLocaleString()} jobs &middot;{" "}
                {indexedStats.cities.toLocaleString()} cities indexed
              </span>
            </div>
          )}

          {activePillCity && zoom >= 10 && (
            <div className="absolute top-4 left-1/2 z-[1000] -translate-x-1/2 overflow-hidden rounded-full border border-white/20 bg-white/25 px-3 py-1.5 shadow-sm shadow-black/5 backdrop-blur-md">
              <span className="text-[10px] font-medium text-gray-700">
                {activePillCity.company_count.toLocaleString()} companies
                &middot; {activePillCity.job_count.toLocaleString()} jobs
              </span>
            </div>
          )}

          <div className="absolute bottom-4 left-4 z-[1000] flex flex-col overflow-hidden rounded-full border border-white/20 bg-white/25 shadow-sm shadow-black/5 backdrop-blur-md">
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
              className="flex h-9 w-9 items-center justify-center text-gray-700 transition-colors hover:bg-white/50"
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
            onToggle={() => setPanelOpen((o) => !o)}
            view={panelView}
            selectedCity={selectedCity}
            onClearCity={handleClearCity}
            companies={companies}
            companiesLoading={companiesLoading}
            onCompanyClick={handleCompanyClick}
            selectedCompany={selectedCompany}
            selectedCompanyLoading={selectedCompanyLoading}
            jobs={jobs}
            jobsLoading={jobsLoading}
            nextCursor={nextCursor}
            loadingMore={loadingMore}
            onLoadMore={handleLoadMore}
            onJobClick={handleJobClick}
            jobDetail={jobDetail}
            jobDetailLoading={jobDetailLoading}
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
