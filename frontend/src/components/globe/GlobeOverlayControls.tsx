import { Home, Minus, Moon, Plus, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { useGlobeStore } from "../../lib/store";

export default function GlobeOverlayControls() {
  const { clearFilters } = useGlobeStore();
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  // Initialize theme tracking on load
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedTheme = localStorage.getItem("theme");
      const systemPreference = window.matchMedia(
        "(prefers-color-scheme: dark)",
      ).matches;

      if (savedTheme === "dark" || (!savedTheme && systemPreference)) {
        document.documentElement.classList.add("dark");
        setTheme("dark");
      } else {
        document.documentElement.classList.remove("dark");
        setTheme("light");
      }
    }
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
    if (typeof window !== "undefined") {
      if (nextTheme === "dark") {
        document.documentElement.classList.add("dark");
        localStorage.setItem("theme", "dark");
      } else {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("theme", "light");
      }
    }
  };

  const handleZoomIn = () => {
    const globe = (window as any).globeInstance;
    if (globe) {
      const pov = globe.pointOfView();
      globe.pointOfView(
        {
          lat: pov.lat,
          lng: pov.lng,
          altitude: Math.max(0.15, pov.altitude * 0.7),
        },
        350,
      );
    }
  };

  const handleZoomOut = () => {
    const globe = (window as any).globeInstance;
    if (globe) {
      const pov = globe.pointOfView();
      globe.pointOfView(
        {
          lat: pov.lat,
          lng: pov.lng,
          altitude: Math.min(3.0, pov.altitude * 1.3),
        },
        350,
      );
    }
  };

  const handleGoHome = () => {
    const globe = (window as any).globeInstance;
    if (globe) {
      globe.pointOfView({ lat: 20, lng: 0, altitude: 2.8 }, 1000);
      clearFilters();
    }
  };

  const buttons = [
    {
      id: "zoom-in",
      label: "Zoom In",
      icon: <Plus className="size-4 text-gray-800 dark:text-gray-200" />,
      action: handleZoomIn,
    },
    {
      id: "zoom-out",
      label: "Zoom Out",
      icon: <Minus className="size-4 text-gray-800 dark:text-gray-200" />,
      action: handleZoomOut,
    },
    {
      id: "home",
      label: "Reset View",
      icon: <Home className="size-4 text-gray-800 dark:text-gray-200" />,
      action: handleGoHome,
    },
    {
      id: "theme",
      label: theme === "light" ? "Dark Mode" : "Light Mode",
      icon:
        theme === "light" ? (
          <Moon className="size-4 text-gray-800" />
        ) : (
          <Sun className="size-4 text-amber-400" />
        ),
      action: toggleTheme,
    },
  ];

  return (
    <div
      id="globe-controls"
      className="absolute bottom-16 left-4 z-20 flex flex-col gap-2 rounded-xl border border-white/20 bg-white/40 p-1 shadow-lg backdrop-blur-md dark:border-white/10 dark:bg-black/40"
    >
      {buttons.map((btn) => (
        <div key={btn.id} className="group/btn relative">
          <button
            id={`btn-${btn.id}`}
            onClick={btn.action}
            type="button"
            className="flex size-9 items-center justify-center rounded-lg transition-all outline-none hover:bg-white/60 active:scale-95 dark:hover:bg-white/10"
            title={btn.label}
          >
            {btn.icon}
          </button>

          {/* Custom micro-animated Tooltip overlay */}
          <div className="pointer-events-none absolute top-1/2 left-12 ml-1 translate-x-[-8px] -translate-y-1/2 scale-90 rounded-md border border-white/10 bg-gray-900/90 px-2.5 py-1 text-[11px] font-medium tracking-tight whitespace-nowrap text-white opacity-0 shadow-md transition-all duration-150 group-hover/btn:translate-x-0 group-hover/btn:scale-100 group-hover/btn:opacity-100 dark:bg-gray-800/95">
            {btn.label}
          </div>
        </div>
      ))}
    </div>
  );
}
