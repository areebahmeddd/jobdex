import { useVirtualizer } from "@tanstack/react-virtual";
import {
  ArrowUpRight,
  Grid,
  Loader2,
  MapPin,
  SlidersHorizontal,
  TrendingUp,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { useCityPins, useFeaturedCities } from "../../hooks/useGlobeData";
import { useJobsList } from "../../hooks/useJobs";
import { PaginatedJobsResponse } from "../../lib/api";
import { useGlobeStore } from "../../lib/store";
import JobCard from "./JobCard";

export default function JobPanel() {
  const {
    zoomLevel,
    activeCity,
    setActiveCity,
    activeRole,
    activeIsRemote,
    activeSeniority,
    activeRegion,
  } = useGlobeStore();

  const [sortBy, setSortBy] = useState<"latest" | "relevance">("latest");
  const parentRef = useRef<HTMLDivElement>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  // Parse active filters for retrieval
  const queryFilters = {
    city: activeCity,
    role_category: activeRole,
    seniority: activeSeniority,
    is_remote: activeIsRemote,
  };

  // Queries
  const { data: cityPins } = useCityPins();
  const { data: featuredCities, isLoading: featuredLoading } =
    useFeaturedCities();
  const {
    data: jobsData,
    isLoading: jobsLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useJobsList(queryFilters);

  // Flatten all jobs pages fetched by InfiniteQuery
  const rawJobs =
    jobsData?.pages.flatMap((page: PaginatedJobsResponse) => page.jobs) || [];

  // Client-side sorting logic
  const sortedJobs = [...rawJobs].sort((a, b) => {
    if (sortBy === "latest") {
      const tA = a.posted_at ? new Date(a.posted_at).getTime() : 0;
      const tB = b.posted_at ? new Date(b.posted_at).getTime() : 0;
      return tB - tA;
    }
    // relevance: Sort by match keyword overlap frequency
    const scoreA =
      (a.tech_stack?.filter(
        (t: string) =>
          activeRole && t.toLowerCase().includes(activeRole.toLowerCase()),
      ).length || 0) +
      (a.title.toLowerCase().includes(activeRole?.toLowerCase() || "") ? 2 : 0);
    const scoreB =
      (b.tech_stack?.filter(
        (t: string) =>
          activeRole && t.toLowerCase().includes(activeRole.toLowerCase()),
      ).length || 0) +
      (b.title.toLowerCase().includes(activeRole?.toLowerCase() || "") ? 2 : 0);

    if (scoreA !== scoreB) return scoreB - scoreA;
    const tA = a.posted_at ? new Date(a.posted_at).getTime() : 0;
    const tB = b.posted_at ? new Date(b.posted_at).getTime() : 0;
    return tB - tA;
  });

  // Calculate active city specific analytics
  const activeCityPin = cityPins?.find(
    (c) => c.name.toLowerCase() === activeCity?.toLowerCase(),
  );

  // Compute global counts if world level
  const totalGlobalJobs =
    cityPins?.reduce((sum, c) => sum + (c.job_count || 0), 0) || 0;
  const totalGlobalCompanies =
    cityPins?.reduce((sum, c) => sum + (c.company_count || 0), 0) || 0;

  const totalJobs = activeCity
    ? activeCityPin?.job_count || sortedJobs.length
    : totalGlobalJobs;
  const totalCompanies = activeCity
    ? activeCityPin?.company_count || 12
    : totalGlobalCompanies;

  // Intersection Observer for infinite scroll trigger
  useEffect(() => {
    if (!hasNextPage || isFetchingNextPage) return;
    const observerTarget = loadMoreRef.current;
    if (!observerTarget) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(observerTarget);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Virtualization setup if listings exceed 50 items for super smooth render speeds
  const isVirtual = sortedJobs.length > 50;
  const rowVirtualizer = useVirtualizer({
    count: sortedJobs.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 170, // JobCard estimated height
    overscan: 5,
  });

  const handleCityClick = (city: any) => {
    setActiveCity(
      city.name,
      { lat: city.latitude, lng: city.longitude },
      city.slug,
    );
    const globe = (window as any).globeInstance;
    if (globe) {
      globe.pointOfView(
        { lat: city.latitude, lng: city.longitude, altitude: 0.6 },
        1200,
      );
    }
  };

  return (
    <div className="relative flex h-full w-full flex-col border-t border-[var(--panel-border)] bg-[var(--panel-bg)] shadow-xl select-none md:border-t-0 md:border-l">
      {/* City/Header section */}
      <div className="shrink-0 space-y-3.5 border-b border-[var(--panel-border)] bg-[var(--card-bg)] p-5 shadow-xs">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            {/* Smooth transition city heading layout */}
            <motion.h2
              layoutId="city-title-header"
              className="text-xl font-extrabold tracking-tight text-neutral-900 capitalize dark:text-neutral-50"
            >
              {activeCity
                ? `${activeCity} Startup Jobs`
                : "Global Hub Discovery"}
            </motion.h2>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-xs font-semibold text-neutral-400 dark:text-neutral-500"
            >
              {totalJobs} registered jobs · {totalCompanies} active companies
            </motion.p>
          </div>

          {/* Sorter Selector */}
          {activeCity && (
            <div className="flex shrink-0 items-center gap-1.5 rounded-lg border border-neutral-200/50 bg-neutral-100 p-1 dark:border-neutral-800 dark:bg-neutral-900">
              <SlidersHorizontal className="size-3 text-neutral-400" />
              <select
                id="panel-sort-by"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="cursor-pointer border-none bg-transparent pr-1 text-[11px] font-bold text-neutral-600 outline-none dark:text-neutral-300"
              >
                <option value="latest">Latest</option>
                <option value="relevance">Relevance</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Body scroll section */}
      <div
        ref={parentRef}
        className="no-scrollbar flex-1 space-y-4 overflow-y-auto p-4"
      >
        <AnimatePresence mode="popLayout">
          {/* A. Empty State or World Hub Explore layout */}
          {!activeCity ? (
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-5"
            >
              {/* Featured cities header info */}
              <div className="space-y-2 rounded-xl border border-neutral-100 bg-gradient-to-br from-indigo-50/40 via-transparent to-transparent p-4 dark:border-neutral-900 dark:from-neutral-900/40 dark:via-neutral-900/10">
                <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
                  <TrendingUp className="size-4 shrink-0" />
                  <span className="text-xs font-bold tracking-wider uppercase">
                    3D Exploration active
                  </span>
                </div>
                <h3 className="text-sm leading-snug font-semibold tracking-tight text-neutral-800 dark:text-neutral-200">
                  Welcome to JobDex interactive globe
                </h3>
                <p className="text-xs leading-relaxed text-neutral-500">
                  Fly around the globe using click-and-drag maneuvers, or select
                  one of our curated featured startup clusters in the panel
                  index below to begin.
                </p>
              </div>

              {/* Curated list / grid section */}
              <div className="space-y-3">
                <div className="flex items-center gap-1.5 text-xs font-bold tracking-wide text-neutral-400 uppercase">
                  <Grid className="size-3 text-neutral-400" />
                  <span>Featured Tech Clusters</span>
                </div>

                {featuredLoading ? (
                  <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2">
                    {[1, 2, 3, 4].map((i) => (
                      <div
                        key={i}
                        className="h-20 animate-pulse rounded-xl bg-neutral-200/50 dark:bg-neutral-800"
                      />
                    ))}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {featuredCities?.map((city) => (
                      <div
                        id={`cluster-card-${city.slug}`}
                        key={city.slug}
                        onClick={() => handleCityClick(city)}
                        className="group relative cursor-pointer rounded-xl border border-neutral-200 bg-white p-3 shadow-xs transition-all hover:border-indigo-500/50 hover:shadow-md active:scale-98 dark:border-neutral-900 dark:bg-neutral-900/60 dark:hover:border-indigo-400/50"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="text-xs font-extrabold text-neutral-800 dark:text-neutral-200">
                              {city.name}
                            </h4>
                            <p className="mt-1 text-[10px] text-neutral-400">
                              {city.region || city.country_code}
                            </p>
                          </div>
                          <span className="rounded-md border border-indigo-100/40 bg-indigo-50 px-1.5 py-0.5 text-[10px] font-bold text-indigo-600 dark:bg-indigo-950/20 dark:text-indigo-400">
                            {city.job_count}+ open
                          </span>
                        </div>
                        <div className="mt-3 flex items-center justify-between border-t border-neutral-50 pt-2 text-[10px] font-semibold tracking-wider text-neutral-400 uppercase dark:border-neutral-900">
                          <span>Explore cluster</span>
                          <ArrowUpRight className="size-3 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          ) : (
            /* B. Cities Feed listing active */
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3.5"
            >
              {/* Query list retrieval loading state feedback */}
              {jobsLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="animate-pulse space-y-3 rounded-xl border border-neutral-200 bg-white p-5 dark:border-neutral-900 dark:bg-neutral-900"
                    >
                      <div className="flex items-center gap-2">
                        <div className="size-9 rounded-md bg-neutral-200 dark:bg-neutral-800" />
                        <div className="flex-1 space-y-1.5">
                          <div className="h-3 w-1/4 rounded bg-neutral-200 dark:bg-neutral-800" />
                          <div className="h-3.5 w-1/2 rounded bg-neutral-200 dark:bg-neutral-800" />
                        </div>
                      </div>
                      <div className="h-3 w-3/4 rounded bg-neutral-200 dark:bg-neutral-800" />
                      <div className="h-10 w-full rounded-lg bg-neutral-200 dark:bg-neutral-800" />
                    </div>
                  ))}
                </div>
              ) : sortedJobs.length === 0 ? (
                /* Empty City list match response */
                <div className="flex flex-col items-center justify-center space-y-3 rounded-2xl border border-dashed border-neutral-200 bg-neutral-50/50 p-12 text-center text-neutral-400 dark:border-neutral-800 dark:bg-neutral-900/10">
                  <MapPin className="size-8 animate-bounce text-neutral-400 dark:text-neutral-600" />
                  <div className="space-y-1">
                    <h4 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">
                      No startup matches found
                    </h4>
                    <p className="max-w-[240px] text-xs leading-relaxed text-neutral-500">
                      We couldn't source any positions aligned with active
                      filters in `{activeCity}`.
                    </p>
                  </div>
                </div>
              ) : (
                /* Primary vertical feed */
                <div className="space-y-3">
                  {isVirtual ? (
                    /* High density virtualization feed representation */
                    <div
                      style={{
                        height: `${rowVirtualizer.getTotalSize()}px`,
                        width: "100%",
                        position: "relative",
                      }}
                    >
                      {rowVirtualizer.getVirtualItems().map((vItem) => {
                        const job = sortedJobs[vItem.index];
                        return (
                          <div
                            key={vItem.key}
                            style={{
                              position: "absolute",
                              top: 0,
                              left: 0,
                              width: "100%",
                              height: `${vItem.size}px`,
                              transform: `translateY(${vItem.start}px)`,
                            }}
                            className="py-1.5"
                          >
                            <JobCard job={job} />
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    /* Standard render flow array for under 50 postings */
                    <div className="space-y-3">
                      {sortedJobs.map((job) => (
                        <JobCard key={job.id} job={job} />
                      ))}
                    </div>
                  )}

                  {/* Endless paginated triggering element */}
                  {hasNextPage && (
                    <div
                      ref={loadMoreRef}
                      className="flex items-center justify-center gap-3 py-6 text-xs font-bold text-neutral-500"
                    >
                      <Loader2 className="size-4 animate-spin text-indigo-500" />
                      <span>Loading more opportunities...</span>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
