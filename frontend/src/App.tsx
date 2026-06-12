import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Briefcase } from "lucide-react";
import { useEffect, useState } from "react";
import GlobeCanvas from "./components/globe/GlobeCanvas";
import GlobeOverlayControls from "./components/globe/GlobeOverlayControls";
import JobDetailDrawer from "./components/jobs/JobDetailDrawer";
import JobPanel from "./components/jobs/JobPanel";
import StatusBar from "./components/layout/StatusBar";
import SearchFilterBar from "./components/search/SearchFilterBar";
import { useGlobeStore } from "./lib/store";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 1000 * 30, // 30 seconds
      retry: 1,
    },
  },
});

function AppMain() {
  const { activeCity, selectedJobId, isDrawerOpen } = useGlobeStore();
  const [isMobile, setIsMobile] = useState(false);
  const [mobilePanelOpen, setMobilePanelOpen] = useState(false);

  // Monitor device size for viewport responsive configurations
  useEffect(() => {
    if (typeof window === "undefined") return;
    const checkIsMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkIsMobile();
    window.addEventListener("resize", checkIsMobile);
    return () => window.removeEventListener("resize", checkIsMobile);
  }, []);

  // When a city is focused on mobile, automatically open the bottom jobs sheet.
  useEffect(() => {
    if (activeCity && isMobile) {
      setMobilePanelOpen(true);
    }
  }, [activeCity, isMobile]);

  // When a job is select opened, ensure sheet displays it on mobile
  useEffect(() => {
    if (selectedJobId && isMobile) {
      setMobilePanelOpen(true);
    }
  }, [selectedJobId, isMobile]);

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden bg-neutral-950 font-sans text-white antialiased md:flex-row">
      {/* 1. GLOBE OVERLAY FRAME (65vw on Wide screen, 100vw on Mobile) */}
      <div className="relative h-[50vh] w-full shrink-0 overflow-hidden border-b border-neutral-900 md:h-full md:w-[65vw] md:border-b-0">
        {/* The primary 3D Canvas WebGL mesh layer */}
        <GlobeCanvas />

        {/* Global floating search and filter control deck */}
        <SearchFilterBar />

        {/* Zoom zoom zoom control floating pad */}
        <GlobeOverlayControls />

        {/* Informational bottom telemetry line */}
        <StatusBar />

        {/* Mobile-only Jobs Index toggle button */}
        {isMobile && (
          <button
            onClick={() => setMobilePanelOpen(!mobilePanelOpen)}
            type="button"
            className="absolute right-4 bottom-12 z-20 flex items-center gap-1.5 rounded-xl border border-white/10 bg-indigo-600 px-3.5 py-2 text-[11px] font-extrabold text-white shadow-2xl outline-none select-none hover:bg-indigo-700 active:scale-95 dark:bg-indigo-500 dark:hover:bg-indigo-400"
          >
            <Briefcase className="size-3.5" />
            <span>
              {mobilePanelOpen ? "Hide Openings" : "Explore Openings"}
            </span>
          </button>
        )}
      </div>

      {/* 2. LATERAL INFORMATION PANEL (35vw on Wide screen, custom transition Sheet on Mobile) */}
      <div
        className={`${
          isMobile
            ? `absolute right-0 bottom-0 left-0 z-30 flex flex-col overflow-hidden rounded-t-2xl border-t border-neutral-800 bg-neutral-900 shadow-2xl transition-all duration-300 ease-out ${
                mobilePanelOpen
                  ? "h-[82vh] opacity-100"
                  : "pointer-events-none h-0 opacity-0"
              }`
            : "relative flex h-full w-[35vw] shrink-0 flex-col overflow-hidden border-l border-neutral-200 dark:border-neutral-900"
        }`}
      >
        {isMobile && mobilePanelOpen && (
          /* Custom swipe-handle indicator */
          <div
            onClick={() => setMobilePanelOpen(false)}
            className="hover:bg-neutral-650 mx-auto my-3 h-1 w-12 shrink-0 cursor-pointer rounded-full bg-neutral-700"
            title="Minimize Panel"
          />
        )}

        {/* Vertical paginated job catalog list */}
        <JobPanel />

        {/* Overlay card descriptor slides */}
        <JobDetailDrawer />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppMain />
    </QueryClientProvider>
  );
}
