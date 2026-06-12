import { useQuery } from "@tanstack/react-query";
import { Compass, Map, Navigation, Wifi, WifiOff } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { fetchHealth } from "../../lib/api";
import { useGlobeStore } from "../../lib/store";

export default function StatusBar() {
  const { zoomLevel, activeCity, activeRole, activeIsRemote } = useGlobeStore();

  // Query health check of Backend directly, polling every 30 seconds
  const { data: health, error } = useQuery({
    queryKey: ["healthStatus"],
    queryFn: fetchHealth,
    refetchInterval: 30000, // 30 seconds polling interval
    retry: 3,
  });

  const isOnline = !!health && !error;

  // Zoom Level Indicators
  const zoomLevelLabels = {
    world: {
      text: "World Exploration",
      icon: <Map className="size-3.5 text-indigo-400" />,
    },
    country: {
      text: "Regional Clusters",
      icon: <Compass className="size-3.5 text-pink-400" />,
    },
    city: {
      text: "Local Micro-Pins",
      icon: <Navigation className="size-3.5 text-emerald-400" />,
    },
  };

  const currentLabel = zoomLevelLabels[zoomLevel] || zoomLevelLabels.world;

  // Active filter breadcrumb logic builder
  const buildBreadcrumb = () => {
    const parts = ["JobDex"];
    if (activeCity) parts.push(activeCity);
    if (activeRole) parts.push(`#${activeRole}`);
    if (activeIsRemote !== null)
      parts.push(activeIsRemote ? "Remote-only" : "Office/Hybrid");
    return parts.join(" › ");
  };

  return (
    <div
      id="app-status-bar"
      className="absolute right-0 bottom-0 left-0 z-10 flex h-8 items-center justify-between border-t border-white/5 bg-black/35 px-4 text-[11px] font-semibold text-white/70 backdrop-blur-sm select-none dark:bg-black/60"
    >
      {/* A. Left - Active Lens/Elevation view */}
      <div className="flex items-center gap-2">
        <AnimatePresence mode="wait">
          <motion.div
            key={zoomLevel}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 8 }}
            transition={{ duration: 0.15 }}
            className="flex items-center gap-1.5"
          >
            {currentLabel.icon}
            <span className="tracking-wide text-white/80 uppercase">
              {currentLabel.text}
            </span>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* B. Center - Breadcrumb trail */}
      <div className="hidden max-w-[50vw] truncate text-white/50 sm:block">
        {buildBreadcrumb()}
      </div>

      {/* C. Right - Telemetry checks */}
      <div className="flex items-center gap-2">
        <span
          className={`inline-block size-1.5 rounded-full ${isOnline ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.7)]" : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.7)]"}`}
        />
        <span className="flex items-center gap-1 font-medium whitespace-nowrap text-white/60">
          {isOnline ? (
            <>
              <Wifi className="size-3 text-emerald-400" />
              <span>Database Server Online</span>
            </>
          ) : (
            <>
              <WifiOff className="size-3 text-red-400" />
              <span>Offline / Connecting</span>
            </>
          )}
        </span>
      </div>
    </div>
  );
}
