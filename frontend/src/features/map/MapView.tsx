import { Cursor } from "@/components/ui/cursor";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  ArrowLeft,
  ChevronDown,
  Home,
  Minus,
  Plus,
  Search,
  SlidersHorizontal,
  Star,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

const HOME_CENTER: L.LatLngTuple = [20, 0];
const HOME_ZOOM = 2;
const GITHUB_REPO = "areebahmeddd/jobdex";
const API_URL = import.meta.env.VITE_API_URL;

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
  const [query, setQuery] = useState("");
  const [connected, setConnected] = useState<boolean | null>(null);
  const [stars, setStars] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function checkHealth() {
      try {
        const res = await fetch(`${API_URL}/health`, {
          signal: AbortSignal.timeout(4000),
        });
        if (!cancelled) setConnected(res.ok);
      } catch {
        if (!cancelled) setConnected(false);
      }
    }
    checkHealth();
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
      zoomControl: false,
    });

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
      {
        maxZoom: 19,
        subdomains: "abcd",
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
      },
    ).addTo(map);

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  function geolocate() {
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
      { timeout: 8000 },
    );
  }

  const [panelOpen, setPanelOpen] = useState(true);
  const isConnected = connected === true;
  const isChecking = connected === null;

  return (
    <div className="flex h-screen flex-col gap-3 bg-gray-50 p-5 font-sans antialiased">
      <Cursor />

      <header className="relative flex shrink-0 items-center">
        <span className="shrink-0 text-4xl font-semibold tracking-tight text-gray-900">
          jobdex
        </span>

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
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search cities, companies, roles.."
                className="w-full rounded-full border border-black/10 bg-white py-2.5 pr-10 pl-10 text-sm text-gray-900 shadow-sm shadow-black/5 outline-none placeholder:text-gray-400 focus:border-black/20"
              />
              <button
                aria-label="Filter"
                className="absolute top-1/2 right-3 -translate-y-1/2 text-gray-400 transition-colors hover:text-gray-700"
              >
                <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
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
            aria-label={`View on GitHub${stars !== null ? ` � ${stars} stars` : ""}`}
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
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search cities, companies, roles.."
            className="w-full rounded-full border border-black/10 bg-white py-2.5 pr-10 pl-10 text-sm text-gray-900 shadow-sm shadow-black/5 outline-none placeholder:text-gray-400 focus:border-black/20"
          />
          <button
            aria-label="Filter"
            className="absolute top-1/2 right-3 -translate-y-1/2 text-gray-400 transition-colors hover:text-gray-700"
          >
            <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="relative flex-1 overflow-hidden rounded-2xl border border-black/10 shadow-lg shadow-black/8">
          <div
            ref={containerRef}
            className="absolute inset-0"
            aria-label="Interactive world map"
          />

          <div className="absolute bottom-4 left-4 z-[1000] flex flex-col overflow-hidden rounded-full border border-white/20 bg-white/25 shadow-sm shadow-black/5 backdrop-blur-md">
            <button
              aria-label="Zoom in"
              onClick={() => mapRef.current?.zoomIn()}
              className="flex h-9 w-9 items-center justify-center text-gray-700 transition-colors hover:bg-white/50"
            >
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
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
              onClick={geolocate}
              className="flex h-9 w-9 items-center justify-center text-gray-700 transition-colors hover:bg-white/50"
            >
              <Home className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>

          <aside
            className={`absolute top-4 right-4 z-[1000] flex w-72 flex-col overflow-hidden rounded-2xl border border-white/20 bg-white/25 shadow-sm shadow-black/5 backdrop-blur-md transition-[height] duration-300 ease-in-out ${
              panelOpen ? "h-[calc(100%-2rem)]" : "h-12"
            }`}
          >
            <div className="flex h-12 shrink-0 items-center justify-between border-b border-white/20 px-3">
              <span className="text-xs font-medium tracking-widest text-gray-500 uppercase">
                Results
              </span>
              <button
                aria-label={panelOpen ? "Collapse panel" : "Expand panel"}
                onClick={() => setPanelOpen((o) => !o)}
                className="flex h-6 w-6 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-white/40 hover:text-gray-700"
              >
                <ChevronDown
                  className={`h-3.5 w-3.5 transition-transform duration-300 ${panelOpen ? "rotate-0" : "rotate-180"}`}
                  aria-hidden="true"
                />
              </button>
            </div>
            <div className="flex flex-1 items-center justify-center">
              <p className="text-sm text-gray-400">No results found</p>
            </div>
          </aside>
        </div>
      </div>

      <style>{`
        .leaflet-control-attribution { font-size: 10px; }

        .location-dot {
          position: relative;
          width: 20px;
          height: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .location-dot::after {
          content: '';
          position: absolute;
          width: 12px;
          height: 12px;
          background: #2563eb;
          border: 2.5px solid #fff;
          border-radius: 50%;
          box-shadow: 0 1px 4px rgba(0,0,0,0.25);
        }
        .location-dot-ring {
          position: absolute;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: rgba(37,99,235,0.15);
          animation: loc-ring 2s ease-out infinite;
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
      `}</style>
    </div>
  );
}
