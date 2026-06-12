import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { ArrowLeft, Locate } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

export function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const [locating, setLocating] = useState(false);
  const [located, setLocated] = useState(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: [20, 0],
      zoom: 2,
      zoomControl: false,
    });

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);

    mapRef.current = map;
    geolocate(map);

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  function geolocate(map: L.Map) {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const { latitude: lat, longitude: lng } = coords;
        map.flyTo([lat, lng], 12, { duration: 1.6 });
        L.marker([lat, lng])
          .addTo(map)
          .bindPopup("<b>You are here</b>")
          .openPopup();
        setLocating(false);
        setLocated(true);
      },
      () => setLocating(false),
      { timeout: 8000 },
    );
  }

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-white">
      <div
        ref={containerRef}
        className="absolute inset-0 z-0"
        aria-label="Interactive world map"
      />

      <div className="absolute top-4 left-4 z-10">
        <Link
          to="/"
          className="flex items-center gap-2 rounded-full border border-black/10 bg-white px-3.5 py-2 text-[13px] font-medium text-gray-700 shadow-sm shadow-black/10 transition-colors hover:bg-gray-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          Back
        </Link>
      </div>

      <div className="absolute right-4 bottom-8 z-10">
        <button
          aria-label={locating ? "Locating…" : "Locate me"}
          onClick={() => mapRef.current && geolocate(mapRef.current)}
          className={`flex h-11 w-11 items-center justify-center rounded-full border bg-white shadow-md shadow-black/10 transition-all ${
            located
              ? "border-black/20 text-black"
              : "border-black/10 text-gray-400 hover:text-gray-800"
          }`}
        >
          <Locate
            className={`h-4 w-4 ${locating ? "animate-pulse" : ""}`}
            aria-hidden="true"
          />
        </button>
      </div>

      <style>{`.leaflet-control-attribution { font-size: 10px; }`}</style>
    </div>
  );
}
