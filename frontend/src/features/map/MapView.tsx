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
  COMPANY_ZOOM_THRESHOLD,
  GITHUB_REPO,
  HOME_CENTER,
  HOME_ZOOM,
  MAP_MAX_ZOOM,
} from "./constants";
import type {
  CityPin,
  CompanyDetail,
  CompanyListItem,
  CompanyOffice,
  CompanyPin,
  Job,
  JobDetail,
  PanelView,
} from "./types";
import { escapeHtml, markerRadius } from "./utils";

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 2C6.477 2 2 6.484 2 12.021c0 4.428 2.865 8.184 6.839 9.504.5.092.682-.217.682-.482 0-.237-.009-.868-.013-1.703-2.782.605-3.369-1.342-3.369-1.342-.454-1.154-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.026 2.747-1.026.546 1.378.202 2.397.1 2.65.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482C19.138 20.2 22 16.447 22 12.021 22 6.484 17.523 2 12 2z" />
    </svg>
  );
}

export function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const locationMarkerRef = useRef<L.Marker | null>(null);
  const hasRequestedLocationRef = useRef(false);
  const permissionStatusRef = useRef<PermissionStatus | null>(null);

  const cityLayerRef = useRef<L.LayerGroup | null>(null);
  const companyLayerRef = useRef<L.LayerGroup | null>(null);
  const officeLayerRef = useRef<L.LayerGroup | null>(null);

  const jobsAbortRef = useRef<AbortController | null>(null);
  const jobDetailAbortRef = useRef<AbortController | null>(null);
  const companiesAbortRef = useRef<AbortController | null>(null);

  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [connected, setConnected] = useState<boolean | null>(null);
  const [stars, setStars] = useState<number | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const [filterOpen, setFilterOpen] = useState(false);
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
  const totalIndexedJobs = cityPins.reduce((s, c) => s + c.job_count, 0);
  const totalIndexedCities = cityPins.filter((c) => c.job_count > 0).length;

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
      const z = map.getZoom();
      setZoom(z);
      if (z >= COMPANY_ZOOM_THRESHOLD) {
        const b = map.getBounds();
        setMapBounds({
          lat_min: b.getSouth(),
          lat_max: b.getNorth(),
          lng_min: b.getWest(),
          lng_max: b.getEast(),
        });
      } else {
        setMapBounds(null);
      }
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
    const map = mapRef.current;
    if (!map || !mapReady || cityPins.length === 0) return;

    cityLayerRef.current?.remove();
    const layer = L.layerGroup();

    cityPins.forEach((pin) => {
      if (!pin.latitude || !pin.longitude) return;
      const r = markerRadius(pin.job_count);
      const marker = L.circleMarker([pin.latitude, pin.longitude], {
        radius: r,
        fillColor: pin.is_featured ? "#4ADE80" : "#86EFAC",
        color: "#ffffff",
        weight: 1.5,
        fillOpacity: pin.is_featured ? 0.9 : 0.75,
        interactive: true,
        className: "city-circle-marker",
      });

      marker.bindTooltip(
        `<div class="map-tt"><strong>${escapeHtml(pin.name)}</strong><span>${pin.job_count.toLocaleString()} jobs &middot; ${pin.company_count} co.</span></div>`,
        {
          direction: "top",
          offset: [0, -6],
          className: "map-tt-wrap",
          sticky: false,
        },
      );

      marker.on("click", () => handleCityClick(pin.name));
      layer.addLayer(marker);
    });

    layer.addTo(map);
    cityLayerRef.current = layer;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cityPins, mapReady]);

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
        renderCompanyPins(mapRef.current, d.companies);
      })
      .catch(() => {});

    return () => ac.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapBounds, roleFilter, remoteFilter]);

  useEffect(() => {
    if (panelView === "companies" && selectedCity) {
      handleCityClick(selectedCity);
    } else if (panelView === "jobs" && selectedCity) {
      loadJobs(selectedCity, null, true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roleFilter, remoteFilter]);

  function renderCompanyPins(map: L.Map, companies: CompanyPin[]) {
    if (!companyLayerRef.current) {
      companyLayerRef.current = L.layerGroup().addTo(map);
    } else {
      companyLayerRef.current.clearLayers();
    }

    companies.slice(0, 80).forEach((co) => {
      if (!co.latitude || !co.longitude) return;

      const wrap = document.createElement("div");
      wrap.className = "company-pin";

      const sources = [
        co.logo_url,
        `https://logo.clearbit.com/${co.slug}.com`,
        `https://www.google.com/s2/favicons?domain=${co.slug}.com&sz=128`,
      ].filter(Boolean) as string[];

      let srcIdx = 0;
      const img = document.createElement("img");
      img.alt = "";
      img.style.cssText = "width:100%;height:100%;object-fit:contain;";

      img.onerror = () => {
        srcIdx += 1;
        if (srcIdx < sources.length) {
          img.src = sources[srcIdx];
        } else {
          wrap.innerHTML = co.name.charAt(0).toUpperCase();
        }
      };

      img.src = sources[0];
      wrap.appendChild(img);

      const icon = L.divIcon({
        className: "",
        html: wrap as unknown as string,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });

      const marker = L.marker([co.latitude, co.longitude], { icon });
      marker.bindTooltip(
        `<div class="map-tt"><strong>${escapeHtml(co.name)}</strong><span>${co.job_count} open roles</span></div>`,
        { direction: "top", offset: [0, -8], className: "map-tt-wrap" },
      );
      companyLayerRef.current?.addLayer(marker);
    });
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

      officeLayerRef.current?.clearLayers();

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
      setSelectedCompany(null);
      setJobDetail(null);
      setPanelView("company-detail");
      setSelectedCompanyLoading(true);
      setJobs([]);
      setNextCursor(null);

      const ac = new AbortController();
      const cityParam = selectedCity
        ? `?city=${encodeURIComponent(selectedCity)}&limit=20`
        : "?limit=20";

      Promise.all([
        fetch(`${API_BASE}/companies/${encodeURIComponent(slug)}`, {
          signal: ac.signal,
        }).then((r) => r.json()),
        fetch(
          `${API_BASE}/companies/${encodeURIComponent(slug)}/jobs${cityParam}`,
          { signal: ac.signal },
        ).then((r) => r.json()),
        fetch(`${API_BASE}/map/companies/${encodeURIComponent(slug)}/offices`, {
          signal: ac.signal,
        }).then((r) => r.json()),
      ])
        .then(([detail, jobsData, officesData]) => {
          setSelectedCompany(detail as CompanyDetail);
          if (jobsData.jobs) {
            setJobs(jobsData.jobs);
            setNextCursor(jobsData.has_more ? "more" : null);
          }
          const map = mapRef.current;
          if (map && officesData.offices?.length) {
            if (!officeLayerRef.current) {
              officeLayerRef.current = L.layerGroup().addTo(map);
            } else {
              officeLayerRef.current.clearLayers();
            }
            (officesData.offices as CompanyOffice[]).forEach((office) => {
              const marker = L.circleMarker(
                [office.latitude, office.longitude],
                {
                  radius: 7,
                  fillColor: "#4ADE80",
                  color: "#ffffff",
                  weight: 2,
                  fillOpacity: 0.95,
                },
              );
              marker.bindTooltip(
                `<div class="map-tt"><strong>${escapeHtml(office.city)}</strong><span>${office.job_count} role${office.job_count !== 1 ? "s" : ""}</span></div>`,
                { direction: "top", offset: [0, -6], className: "map-tt-wrap" },
              );
              officeLayerRef.current?.addLayer(marker);
            });
            if (selectedCity) {
              const match = (officesData.offices as CompanyOffice[]).find(
                (o) => o.city.toLowerCase() === selectedCity.toLowerCase(),
              );
              const target = match ?? officesData.offices[0];
              map.flyTo([target.latitude, target.longitude], 10, {
                duration: 1.2,
              });
            } else {
              const bounds = L.latLngBounds(
                officesData.offices.map((o: CompanyOffice) => [
                  o.latitude,
                  o.longitude,
                ]),
              );
              map.flyToBounds(bounds.pad(0.4), { duration: 1.2, maxZoom: 10 });
            }
          }
        })
        .catch(() => {})
        .finally(() => setSelectedCompanyLoading(false));
    },
    [selectedCity],
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
      const cityParam = selectedCity
        ? `&city=${encodeURIComponent(selectedCity)}`
        : "";
      fetch(
        `${API_BASE}/companies/${encodeURIComponent(selectedCompany.slug)}/jobs?limit=20&offset=${jobs.length}${cityParam}`,
      )
        .then((r) => r.json())
        .then((d) => {
          if (d.jobs) {
            setJobs((prev) => [...prev, ...d.jobs]);
            setNextCursor(d.has_more ? "more" : null);
          }
        })
        .catch(() => {});
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
      officeLayerRef.current?.clearLayers();
      setSelectedCompany(null);
      setPanelView(selectedCity ? "companies" : "default");
    }
  }

  function handleClearCity() {
    officeLayerRef.current?.clearLayers();
    setSelectedCity(null);
    setSelectedCompany(null);
    setCompanies([]);
    setJobs([]);
    setNextCursor(null);
    setPanelView("default");
    setQuery("");
  }

  const geolocate = useCallback((forceFresh = false) => {
    const map = mapRef.current;
    if (!map || !navigator.geolocation) return;

    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const { latitude: lat, longitude: lng } = coords;
        map.flyTo([lat, lng], 12, { duration: 1.6 });
        locationMarkerRef.current?.remove();
        const icon = L.divIcon({
          className: "",
          html: `<div class="location-dot"><div class="location-dot-ring"></div></div>`,
          iconSize: [20, 20],
          iconAnchor: [10, 10],
        });
        locationMarkerRef.current = L.marker([lat, lng], { icon }).addTo(map);
      },
      () => {},
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: forceFresh ? 0 : 5 * 60 * 1000,
      },
    );
  }, []);

  useEffect(() => {
    if (!mapReady || !mapRef.current || !navigator.geolocation) return;

    let disposed = false;

    const requestLocation = async () => {
      if (!navigator.permissions?.query) {
        if (!hasRequestedLocationRef.current) {
          hasRequestedLocationRef.current = true;
          geolocate();
        }
        return;
      }

      try {
        const status = await navigator.permissions.query({
          name: "geolocation",
        });
        if (disposed) return;

        permissionStatusRef.current = status;

        if (status.state === "granted") {
          geolocate();
        } else if (
          status.state === "prompt" &&
          !hasRequestedLocationRef.current
        ) {
          hasRequestedLocationRef.current = true;
          geolocate();
        }

        status.onchange = () => {
          if (status.state === "granted") {
            geolocate(true);
          }
        };
      } catch {
        if (!hasRequestedLocationRef.current) {
          hasRequestedLocationRef.current = true;
          geolocate();
        }
      }
    };

    void requestLocation();

    return () => {
      disposed = true;
      if (permissionStatusRef.current) {
        permissionStatusRef.current.onchange = null;
      }
    };
  }, [geolocate, mapReady]);

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

            <div className="relative w-96">
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
          className="ml-auto inline-flex shrink-0 items-center gap-1 rounded-full border border-black/10 bg-white/90 px-2 py-1.5 shadow-sm shadow-black/5 backdrop-blur-md"
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
        <div className="relative w-full">
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

          {zoom >= COMPANY_ZOOM_THRESHOLD && (
            <div className="pointer-events-none absolute top-4 left-1/2 z-[1000] -translate-x-1/2">
              <span className="rounded-full border border-black/8 bg-white/80 px-3 py-1 text-[11px] text-gray-500 shadow-sm backdrop-blur-sm">
                Company view
              </span>
            </div>
          )}

          {cityPins.length > 0 && (
            <div className="absolute top-4 left-4 z-[1000] overflow-hidden rounded-full border border-white/20 bg-white/25 px-3 py-1.5 shadow-sm shadow-black/5 backdrop-blur-md">
              <span className="text-[10px] font-medium text-gray-700">
                {totalIndexedJobs.toLocaleString()} jobs &middot;{" "}
                {totalIndexedCities} cities indexed
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
              aria-label="Go to my location"
              onClick={() => geolocate(true)}
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

        .location-dot {
          position: relative; width: 20px; height: 20px;
          display: flex; align-items: center; justify-content: center;
        }
        .location-dot::after {
          content: ''; position: absolute; width: 12px; height: 12px;
          background: #2563eb; border: 2.5px solid #fff; border-radius: 50%;
          box-shadow: 0 1px 4px rgba(0,0,0,0.25);
        }
        .location-dot-ring {
          position: absolute; width: 32px; height: 32px; border-radius: 50%;
          background: rgba(37,99,235,0.15); animation: loc-ring 2s ease-out infinite;
        }
        @keyframes loc-ring {
          0%   { transform: scale(0.4); opacity: 0.8; }
          100% { transform: scale(1);   opacity: 0; }
        }

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

        .city-circle-marker { cursor: pointer; }

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
