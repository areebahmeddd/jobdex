import { Briefcase, Globe2, Layers, Search, UserCheck, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { useGlobeStore } from "../../lib/store";

const ROLE_CATEGORIES = [
  "engineering",
  "design",
  "product",
  "marketing",
  "sales",
  "data",
  "operations",
];

const SENIORITIES = [
  "intern",
  "junior",
  "mid",
  "senior",
  "lead",
  "staff",
  "principal",
  "director",
  "vp",
  "c-level",
];

const REGIONS = [
  { code: "US", label: "United States" },
  { code: "GB", label: "United Kingdom" },
  { code: "EU", label: "Europe" },
  { code: "APAC", label: "Asia Pacific" },
  { code: "CA", label: "Canada" },
];

export default function SearchFilterBar() {
  const {
    activeCity,
    activeCityCoords,
    setActiveCity,
    activeRole,
    activeIsRemote,
    activeSeniority,
    activeRegion,
    setFilter,
    clearFilters,
  } = useGlobeStore();

  const [inputVal, setInputVal] = useState(activeRole || "");

  // Synchronize local input state if activeRole changes globally
  useEffect(() => {
    setInputVal(activeRole || "");
  }, [activeRole]);

  const handleSearchSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setFilter("activeRole", inputVal.trim() || null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSearchSubmit();
    }
  };

  const clearCity = () => {
    setActiveCity(null);
    const globe = (window as any).globeInstance;
    if (globe) {
      globe.pointOfView({ lat: 20, lng: 0, altitude: 2.8 }, 1100);
    }
  };

  const toggleRemote = () => {
    if (activeIsRemote === null) {
      setFilter("activeIsRemote", true);
    } else if (activeIsRemote === true) {
      setFilter("activeIsRemote", false);
    } else {
      setFilter("activeIsRemote", null);
    }
  };

  const selectSeniority = (val: string) => {
    setFilter("activeSeniority", val === "all" ? null : val);
  };

  const selectRegion = (val: string) => {
    setFilter("activeRegion", val === "all" ? null : val);
  };

  const toggleCategory = (category: string) => {
    if (activeRole?.toLowerCase() === category.toLowerCase()) {
      setFilter("activeRole", null);
      setInputVal("");
    } else {
      setFilter("activeRole", category);
      setInputVal(category);
    }
  };

  const hasActiveFilters =
    !!activeCity ||
    activeIsRemote !== null ||
    !!activeRole ||
    !!activeSeniority ||
    !!activeRegion;

  return (
    <motion.div
      initial={{ y: -16, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: "spring", stiffness: 350, damping: 28 }}
      className="absolute top-4 left-1/2 z-50 flex w-[calc(100%-2rem)] max-w-[580px] -translate-x-1/2 flex-col items-center gap-2"
    >
      {/* Primary Input Container */}
      <div className="flex w-full flex-col items-stretch gap-1.5 rounded-2xl border border-white/20 bg-white/70 p-1.5 shadow-2xl backdrop-blur-xl transition-all duration-300 md:flex-row dark:border-white/10 dark:bg-black/45">
        {/* Active City Badge inside input */}
        <div className="flex items-center gap-1">
          <AnimatePresence mode="popLayout">
            {activeCity && (
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
                className="flex h-9 items-center gap-1.5 rounded-xl bg-indigo-600 pr-2 pl-3 text-xs font-semibold whitespace-nowrap text-white shadow-md dark:bg-indigo-500"
              >
                <span>{activeCity}</span>
                <button
                  onClick={clearCity}
                  type="button"
                  className="flex items-center justify-center rounded-full p-0.5 transition-all outline-none hover:bg-white/20 active:scale-90"
                  title="Clear City Selection"
                >
                  <X className="size-3" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Input Wrapper */}
        <div className="relative flex h-10 flex-1 items-center px-2">
          <Search className="mr-2 size-4 shrink-0 text-gray-400 dark:text-gray-500" />
          <input
            id="role-search-input"
            type="text"
            placeholder="Search roles, skills, or tech stacks..."
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={handleKeyDown}
            className="h-full w-full border-none bg-transparent text-sm font-medium text-gray-800 placeholder-gray-400 outline-none focus:ring-0 dark:text-gray-100 dark:placeholder-gray-500"
          />
          {inputVal && (
            <button
              onClick={() => {
                setInputVal("");
                setFilter("activeRole", null);
              }}
              type="button"
              className="absolute right-3 rounded-full p-1 text-gray-400 transition-colors hover:text-gray-600 dark:hover:text-gray-200"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>

        {/* Quick Search Action Button */}
        <button
          onClick={() => handleSearchSubmit()}
          type="button"
          className="flex h-10 shrink-0 items-center justify-center gap-1.5 rounded-xl bg-gray-900 px-4 text-xs font-semibold tracking-wide text-white shadow-md transition-all hover:bg-gray-800 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100"
        >
          <Search className="size-3.5" />
          <span>Explore</span>
        </button>
      </div>

      {/* Filter Options Row */}
      <div className="no-scrollbar flex h-11 w-full items-center gap-2 overflow-x-auto rounded-xl border border-white/10 bg-white/55 px-3 py-1 shadow-md backdrop-blur-lg dark:bg-black/30">
        {/* Remote Toggle badge button */}
        <button
          id="toggle-remote"
          onClick={toggleRemote}
          type="button"
          className={`flex h-[28px] items-center gap-1 rounded-lg border px-3 py-1 text-xs font-semibold tracking-tight whitespace-nowrap transition-all duration-200 ${
            activeIsRemote === true
              ? "border-violet-500/30 bg-violet-600/10 text-violet-600 dark:text-violet-400"
              : activeIsRemote === false
                ? "border-amber-500/30 bg-amber-600/10 text-amber-600"
                : "border-gray-200 bg-transparent text-gray-600 hover:border-gray-300 dark:border-white/10 dark:text-gray-400 dark:hover:border-white/20"
          }`}
        >
          <Globe2 className="size-3" />
          <span>
            {activeIsRemote === true
              ? "Fully Remote"
              : activeIsRemote === false
                ? "Onsite / Hybrid"
                : "All Locations"}
          </span>
        </button>

        <span className="h-4 w-px shrink-0 bg-gray-300 dark:bg-gray-700" />

        {/* Seniority Dropdown */}
        <div className="relative shrink-0">
          <select
            id="select-seniority"
            value={activeSeniority || "all"}
            onChange={(e) => selectSeniority(e.target.value)}
            className="h-[28px] cursor-pointer appearance-none rounded-lg border border-gray-200 bg-transparent py-0.5 pr-6 pl-2 font-sans text-xs font-semibold text-gray-600 outline-none hover:border-gray-300 focus:ring-0 dark:border-white/10 dark:text-gray-300 dark:hover:border-white/20"
          >
            <option
              value="all"
              className="bg-white text-gray-800 dark:bg-gray-900 dark:text-white"
            >
              Seniority
            </option>
            {SENIORITIES.map((level) => (
              <option
                key={level}
                value={level}
                className="bg-white text-gray-800 dark:bg-gray-900 dark:text-white"
              >
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute top-1/2 right-2 -translate-y-1/2 border-t-[4px] border-r-[3.5px] border-l-[3.5px] border-t-gray-500 border-r-transparent border-l-transparent" />
        </div>

        {/* Region Dropdown */}
        <div className="relative shrink-0">
          <select
            id="select-region"
            value={activeRegion || "all"}
            onChange={(e) => selectRegion(e.target.value)}
            className="h-[28px] cursor-pointer appearance-none rounded-lg border border-gray-200 bg-transparent py-0.5 pr-6 pl-2 font-sans text-xs font-semibold text-gray-600 outline-none hover:border-gray-300 focus:ring-0 dark:border-white/10 dark:text-gray-300 dark:hover:border-white/20"
          >
            <option
              value="all"
              className="bg-white text-gray-800 dark:bg-gray-900 dark:text-white"
            >
              Region
            </option>
            {REGIONS.map((reg) => (
              <option
                key={reg.code}
                value={reg.code}
                className="bg-white text-gray-800 dark:bg-gray-900 dark:text-white"
              >
                {reg.label}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute top-1/2 right-2 -translate-y-1/2 border-t-[4px] border-r-[3.5px] border-l-[3.5px] border-t-gray-500 border-r-transparent border-l-transparent" />
        </div>

        <span className="h-4 w-px shrink-0 bg-gray-300 dark:bg-gray-700" />

        {/* Category badglets */}
        {ROLE_CATEGORIES.map((cat) => {
          const isActive = activeRole?.toLowerCase() === cat.toLowerCase();
          return (
            <button
              key={cat}
              onClick={() => toggleCategory(cat)}
              type="button"
              className={`h-[28px] rounded-lg border px-3.5 py-1 text-xs font-bold tracking-tight whitespace-nowrap ring-0 transition-all outline-none ${
                isActive
                  ? "border-indigo-505 scale-102 bg-indigo-600 text-white shadow-sm"
                  : "border-gray-200 bg-white/40 text-gray-600 hover:bg-white/70 dark:border-white/5 dark:bg-white/5 dark:text-gray-400 dark:hover:bg-white/10"
              }`}
            >
              #{cat}
            </button>
          );
        })}
      </div>

      {/* Dismissable badges representing active filters below the search bar */}
      <AnimatePresence>
        {hasActiveFilters && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex max-w-full flex-wrap items-center justify-center gap-1.5 py-1"
          >
            {/* Clear All action bubble */}
            <button
              onClick={clearFilters}
              type="button"
              className="inline-flex items-center gap-1 rounded-full border border-white/20 bg-white/75 px-3 py-1 text-[11px] font-bold text-gray-500 transition-colors outline-none hover:text-red-500 dark:border-white/10 dark:bg-black/50"
            >
              <span>Clear Search</span>
              <X className="size-3" />
            </button>

            {/* Role Filter */}
            {activeRole && (
              <div className="inline-flex items-center gap-1 rounded-full border border-indigo-200/50 bg-indigo-50/70 px-2.5 py-1 text-[11px] font-semibold text-indigo-700 dark:border-indigo-900/40 dark:bg-indigo-950/40 dark:text-indigo-300">
                <Briefcase className="size-2.5 shrink-0" />
                <span>Role: {activeRole}</span>
                <button
                  onClick={() => {
                    setFilter("activeRole", null);
                    setInputVal("");
                  }}
                  type="button"
                  className="rounded-full p-0.5 transition-colors hover:bg-indigo-200 dark:hover:bg-indigo-900/60"
                >
                  <X className="size-2.5" />
                </button>
              </div>
            )}

            {/* IsRemote Filter */}
            {activeIsRemote !== null && (
              <div className="inline-flex items-center gap-1 rounded-full border border-violet-200/50 bg-violet-50/70 px-2.5 py-1 text-[11px] font-semibold text-violet-700 dark:border-violet-900/40 dark:bg-violet-950/40 dark:text-violet-300">
                <Globe2 className="size-2.5 shrink-0" />
                <span>{activeIsRemote ? "Remote Only" : "Office/Hybrid"}</span>
                <button
                  onClick={() => setFilter("activeIsRemote", null)}
                  type="button"
                  className="rounded-full p-0.5 transition-colors hover:bg-violet-200 dark:hover:bg-violet-900/60"
                >
                  <X className="size-2.5" />
                </button>
              </div>
            )}

            {/* Seniority Filter */}
            {activeSeniority && (
              <div className="inline-flex items-center gap-1 rounded-full border border-amber-200/50 bg-amber-50/70 px-2.5 py-1 text-[11px] font-semibold text-amber-700 dark:border-amber-900/40 dark:bg-amber-950/40 dark:text-amber-300">
                <UserCheck className="size-2.5 shrink-0" />
                <span>Rank: {activeSeniority}</span>
                <button
                  onClick={() => setFilter("activeSeniority", null)}
                  type="button"
                  className="rounded-full p-0.5 transition-colors hover:bg-amber-200 dark:hover:bg-amber-900/60"
                >
                  <X className="size-2.5" />
                </button>
              </div>
            )}

            {/* Region Filter */}
            {activeRegion && (
              <div className="inline-flex items-center gap-1 rounded-full border border-emerald-200/50 bg-emerald-50/70 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/40 dark:text-emerald-300">
                <Layers className="size-2.5 shrink-0" />
                <span>Region: {activeRegion}</span>
                <button
                  onClick={() => setFilter("activeRegion", null)}
                  type="button"
                  className="rounded-full p-0.5 transition-colors hover:bg-emerald-200 dark:hover:bg-emerald-900/60"
                >
                  <X className="size-2.5" />
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
