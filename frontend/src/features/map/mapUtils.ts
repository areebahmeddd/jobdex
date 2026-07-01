import { escapeHtml } from "@/lib/utils";
import type { CompanyPin } from "@/types";
import L from "leaflet";

const GOLDEN_ANGLE = 2.39996323;
const MAX_SPREAD = 0.018;

export function renderCompanyPins(
  map: L.Map,
  layerRef: { current: L.LayerGroup | null },
  companies: CompanyPin[],
  onCompanyClick: (slug: string) => void,
) {
  if (!layerRef.current) {
    layerRef.current = L.layerGroup().addTo(map);
  } else {
    layerRef.current.clearLayers();
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
    const sorted = [...group].sort((a, b) => b.job_count - a.job_count);
    const c = MAX_SPREAD / Math.sqrt(sorted.length);

    sorted.forEach((co, idx) => {
      let lat = co.latitude!;
      let lng = co.longitude!;

      if (sorted.length > 1) {
        const r = c * Math.sqrt(idx + 1);
        const theta = idx * GOLDEN_ANGLE;
        lat += r * Math.sin(theta);
        lng += r * Math.cos(theta);
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
      layerRef.current?.addLayer(marker);
    });
  }
}
