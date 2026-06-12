import { useEffect, useRef, useState } from "react";
import { useCityPins, useCompanyPins } from "../../hooks/useGlobeData";
import { fetchCompanyJobs } from "../../lib/api";
import { useGlobeStore } from "../../lib/store";

export default function GlobeCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeInstanceRef = useRef<any>(null);
  const [GlobeLib, setGlobeLib] = useState<any>(null);

  // Subscribe to Zustand store values
  const {
    zoomLevel,
    setZoomLevel,
    activeCity,
    activeCityCoords,
    setActiveCity,
    openJob,
    viewportBounds,
    activeRole,
    activeIsRemote,
    activeCountryCode,
  } = useGlobeStore();

  // Queries
  const { data: cityPins } = useCityPins();

  // Company pins filters based on estimated viewport bounds & store parameters
  const companyFilters = {
    lat_min: viewportBounds?.lat_min || -90,
    lat_max: viewportBounds?.lat_max || 90,
    lng_min: viewportBounds?.lng_min || -180,
    lng_max: viewportBounds?.lng_max || 180,
    role: activeRole,
    is_remote: activeIsRemote,
    country_code: activeCountryCode,
  };

  const isCityZoom = zoomLevel === "city";
  const { data: companyPins } = useCompanyPins(companyFilters, isCityZoom);

  // 1. Asynchronously load globe.gl client side only
  useEffect(() => {
    import("globe.gl")
      .then((mod) => {
        setGlobeLib(() => mod.default);
      })
      .catch((err) => {
        console.error("Failed to load globe.gl dynamically:", err);
      });
  }, []);

  // 2. Initialize the Globe component when library and ref are ready
  useEffect(() => {
    if (!GlobeLib || !containerRef.current || globeInstanceRef.current) return;

    const globe = GlobeLib()(containerRef.current);
    globeInstanceRef.current = globe;
    (window as any).globeInstance = globe;

    // Configure globe visual themes
    globe
      .globeImageUrl("//unpkg.com/three-globe/example/img/earth-dark.jpg")
      .backgroundColor("rgba(0,0,0,0)")
      .atmosphereColor("#7c3aed")
      .atmosphereAltitude(0.15)
      .showAtmosphere(true);

    // Auto rotate slow speed on start
    const controls = globe.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.15;

    // Stop auto-rotating on user interaction
    const stopAutoRotate = () => {
      controls.autoRotate = false;
    };
    controls.addEventListener("start", stopAutoRotate);

    // Zoom and camera tracking listener
    const handleCameraChange = () => {
      const camera = globe.camera();
      const pos = camera.position;

      // Default globe.gl globe radius is 100 units
      const distance = Math.sqrt(pos.x * pos.x + pos.y * pos.y + pos.z * pos.z);
      const altitude = distance / 100 - 1;

      // Identify zoom thresholds
      // world: > 2.5
      // country: 0.8–2.5
      // city: < 0.8
      let newLevel: "world" | "country" | "city" = "world";
      if (altitude < 0.8) {
        newLevel = "city";
      } else if (altitude <= 2.5) {
        newLevel = "country";
      } else {
        newLevel = "world";
      }

      // Estimate current center lat & lng
      let centerLat = 0;
      let centerLng = 0;
      if (typeof globe.toGeodeticCoords === "function") {
        const coords = globe.toGeodeticCoords(pos.x, pos.y, pos.z);
        if (coords) {
          centerLat = coords.lat;
          centerLng = coords.lng;
        }
      } else if (controls.getPolarAngle && controls.getAzimuthalAngle) {
        // Fallback mathematical angles projection
        centerLat = 90 - (controls.getPolarAngle() * 180) / Math.PI;
        centerLng = (-controls.getAzimuthalAngle() * 180) / Math.PI;
        // Normalize lng
        centerLng = ((centerLng + 180) % 360) - 180;
      }

      // Compute bounding box based on altitude span
      const lat_span = Math.min(90, 45 * altitude);
      const lng_span = Math.min(180, 90 * altitude);

      const bounds = {
        lat_min: Math.max(-90, centerLat - lat_span),
        lat_max: Math.min(90, centerLat + lat_span),
        lng_min: centerLng - lng_span,
        lng_max: centerLng + lng_span,
      };

      setZoomLevel(newLevel, bounds);

      // Client-side Euclidean distance nearest city helper
      if (
        newLevel === "city" &&
        !useGlobeStore.getState().activeCity &&
        cityPins &&
        cityPins.length > 0
      ) {
        let nearestCity = null;
        let bestDistance = Infinity;

        for (const city of cityPins) {
          const latDiff = city.latitude - centerLat;
          let lngDiff = city.longitude - centerLng;
          // normalize wrap around 180
          if (lngDiff > 180) lngDiff -= 360;
          if (lngDiff < -180) lngDiff += 360;

          const dSquared = latDiff * latDiff + lngDiff * lngDiff;
          if (dSquared < bestDistance) {
            bestDistance = dSquared;
            nearestCity = city;
          }
        }

        // Only snap to city is it's within a sensible proximity threshold
        if (nearestCity && bestDistance < 200) {
          setActiveCity(
            nearestCity.name,
            { lat: nearestCity.latitude, lng: nearestCity.longitude },
            nearestCity.slug,
          );
        }
      }
    };

    controls.addEventListener("change", handleCameraChange);

    return () => {
      controls.removeEventListener("start", stopAutoRotate);
      controls.removeEventListener("change", handleCameraChange);
    };
  }, [GlobeLib, cityPins]);

  // 3. Keep dimensions tracked via ResizeObserver
  useEffect(() => {
    if (!globeInstanceRef.current || !containerRef.current) return;
    const container = containerRef.current;
    const globe = globeInstanceRef.current;

    const resizeObserver = new ResizeObserver((entries) => {
      if (!entries || entries.length === 0) return;
      const { width, height } = entries[0].contentRect;
      globe.width(width).height(height);
    });

    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
    };
  }, [GlobeLib]);

  // 4. Update data layers on cityPins or companyPins change
  useEffect(() => {
    if (!globeInstanceRef.current) return;
    const globe = globeInstanceRef.current;

    const pinPoints = zoomLevel !== "city" ? cityPins || [] : [];

    globe
      .pointsData(pinPoints)
      .pointLat("latitude")
      .pointLng("longitude")
      .pointColor((d: any) => {
        const count = d.job_count || 0;
        return count < 10 ? "#6366f1" : count < 50 ? "#8b5cf6" : "#a855f7";
      })
      .pointAltitude((d: any) =>
        Math.min(0.005 + (d.job_count || 0) * 0.0005, 0.04),
      )
      .pointRadius((d: any) => Math.min(0.3 + (d.job_count || 0) * 0.01, 1.5))
      .onPointClick((d: any) => {
        setActiveCity(d.name, { lat: d.latitude, lng: d.longitude }, d.slug);
        globe.pointOfView(
          { lat: d.latitude, lng: d.longitude, altitude: 0.6 },
          1200,
        );
      });
  }, [cityPins, zoomLevel]);

  // 5. Update HTML markers overlay for Close-up View (city level)
  useEffect(() => {
    if (!globeInstanceRef.current) return;
    const globe = globeInstanceRef.current;

    const closeUpCompanies = zoomLevel === "city" ? companyPins || [] : [];
    // Cap at 200 items for high performance rendering limits
    const displayCompanies = closeUpCompanies.slice(0, 200);

    globe
      .htmlElementsData(displayCompanies)
      .htmlLat("latitude")
      .htmlLng("longitude")
      .htmlElement((d: any) => {
        const el = document.createElement("div");
        el.className = "globe-pin";

        const logo = document.createElement("div");
        logo.className = "globe-pin-logo";

        if (d.logo_url) {
          const img = document.createElement("img");
          img.src = d.logo_url;
          img.alt = d.name;
          img.className = "w-full h-full object-cover rounded-full";
          img.referrerPolicy = "no-referrer";
          img.onerror = () => {
            img.style.display = "none";
            logo.textContent = d.name.charAt(0).toUpperCase();
            logo.style.backgroundColor = "#8b5cf6";
            logo.style.color = "#ffffff";
          };
          logo.appendChild(img);
        } else {
          logo.textContent = d.name.charAt(0).toUpperCase();
          logo.style.backgroundColor = "#8b5cf6";
          logo.style.color = "#ffffff";
        }

        const dot = document.createElement("div");
        dot.className = "globe-pin-dot";

        el.appendChild(logo);
        el.appendChild(dot);

        // Click on company pin fetches and opens the first available job
        el.addEventListener("click", async (e) => {
          e.stopPropagation();
          try {
            // Visually pulse on selection
            logo.classList.add("pin-pulse-active");

            const jobs = await fetchCompanyJobs(d.slug, 1);
            if (jobs && jobs.length > 0) {
              openJob(jobs[0].id);
            } else {
              // fallback if no jobs found, at least set and focus active city
              setActiveCity(d.city);
            }
          } catch (err) {
            console.error("Error opening company job:", err);
          } finally {
            setTimeout(() => {
              logo.classList.remove("pin-pulse-active");
            }, 3000);
          }
        });

        return el;
      });
  }, [companyPins, zoomLevel]);

  // 6. Fly Camera to Active City if changed externally
  useEffect(() => {
    if (!globeInstanceRef.current || !activeCityCoords) return;
    const { lat, lng } = activeCityCoords;
    globeInstanceRef.current.pointOfView({ lat, lng, altitude: 0.6 }, 1200);
  }, [activeCityCoords]);

  return (
    <div className="relative h-full w-full">
      <div
        ref={containerRef}
        className="h-full w-full cursor-grab outline-none active:cursor-grabbing"
      />
    </div>
  );
}
