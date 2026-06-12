import DOMPurify from "dompurify";
import {
  Award,
  Briefcase,
  Calendar,
  ChevronDown,
  ChevronLeft,
  ChevronUp,
  Clock,
  ExternalLink,
  Globe,
  Loader2,
  MapPin,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import {
  useCompanyDetailQuery,
  useCompanyJobsQuery,
  useJobDetailQuery,
} from "../../hooks/useJobDetail";
import { useGlobeStore } from "../../lib/store";
import { formatRelativeTime } from "../../lib/utils";

export default function JobDetailDrawer() {
  const { selectedJobId, isDrawerOpen, closeJob, openJob } = useGlobeStore();
  const [isMobile, setIsMobile] = useState(false);
  const [descExpanded, setDescExpanded] = useState(false);

  // Responsive device checks
  useEffect(() => {
    if (typeof window === "undefined") return;
    const checkIsMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkIsMobile();
    window.addEventListener("resize", checkIsMobile);
    return () => window.removeEventListener("resize", checkIsMobile);
  }, []);

  // Fetch job details
  const {
    data: job,
    isLoading: jobLoading,
    error: jobError,
  } = useJobDetailQuery(selectedJobId);

  // Fetch company details reactively once job info loads
  const companySlug = job?.company_slug || null;
  const { data: company, isLoading: companyLoading } =
    useCompanyDetailQuery(companySlug);
  const { data: relatedJobs, isLoading: jobsLoading } = useCompanyJobsQuery(
    companySlug,
    6,
  );

  // Reset scroll and description states on job ID change
  useEffect(() => {
    setDescExpanded(false);
    const container = document.getElementById("drawer-scroll-container");
    if (container) container.scrollTop = 0;
  }, [selectedJobId]);

  if (!isDrawerOpen) return null;

  const sanitizedDescription = job?.description
    ? DOMPurify.sanitize(job.description)
    : "";

  // Palette color helper for logo fallback
  const fallbackColors = [
    "bg-red-500/10 text-red-600 border border-red-500/20 dark:bg-red-950/40 dark:text-red-400 dark:border-red-900/30",
    "bg-blue-500/10 text-blue-600 border border-blue-500/20 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-900/30",
    "bg-green-500/10 text-green-600 border border-green-500/20 dark:bg-green-950/40 dark:text-green-400 dark:border-green-900/30",
    "bg-amber-500/10 text-amber-600 border border-amber-500/20 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-900/30",
    "bg-purple-500/10 text-purple-600 border border-purple-500/20 dark:bg-purple-950/40 dark:text-purple-400 dark:border-purple-900/30",
    "bg-cyan-500/10 text-cyan-600 border border-cyan-500/20 dark:bg-cyan-950/40 dark:text-cyan-400 dark:border-cyan-900/30",
  ];
  const charCodeIndex = job?.company_name
    ? job.company_name.charCodeAt(0) % 6
    : 0;
  const fallbackColorStyle = fallbackColors[charCodeIndex];

  // Animation variants
  const drawerVariants = {
    hidden: isMobile ? { y: "100%", opacity: 0.95 } : { x: "100%" },
    visible: isMobile ? { y: 0, opacity: 1 } : { x: 0 },
    exit: isMobile ? { y: "100%", opacity: 0.95 } : { x: "100%" },
  };

  const springTransition = {
    type: "spring" as const,
    stiffness: 380,
    damping: 32,
  };

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={selectedJobId || "empty"}
        initial="hidden"
        animate="visible"
        exit="exit"
        variants={drawerVariants}
        transition={springTransition}
        className="shadow-3xl absolute top-0 right-0 z-40 flex h-full w-full flex-col border-l border-neutral-200 bg-white focus:outline-none md:w-[35vw] md:min-w-[420px] dark:border-neutral-900 dark:bg-neutral-950"
      >
        {/* Sticky Drawer Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-neutral-100 bg-white/85 px-4 py-3 backdrop-blur-md dark:border-neutral-900 dark:bg-neutral-950/85">
          <button
            onClick={closeJob}
            type="button"
            className="inline-flex items-center gap-1 text-xs font-semibold text-neutral-500 transition-colors hover:text-indigo-600 dark:text-neutral-400 dark:hover:text-indigo-400"
          >
            <ChevronLeft className="size-4" />
            <span>Discover Roles</span>
          </button>

          {job?.source_url && (
            <button
              onClick={() =>
                window.open(job.source_url, "_blank", "noopener,noreferrer")
              }
              type="button"
              className="flex items-center justify-center gap-1 rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-extrabold text-white shadow-sm transition-all hover:bg-indigo-700 active:scale-97 dark:bg-indigo-500 dark:hover:bg-indigo-400"
            >
              <span>Apply Now</span>
              <ExternalLink className="size-3" />
            </button>
          )}
        </div>

        {/* Fetch Loading States */}
        {jobLoading ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-neutral-500">
            <Loader2 className="size-7 animate-spin text-indigo-500" />
            <p className="text-xs font-medium tracking-tight">
              Sourcing detailed career data...
            </p>
          </div>
        ) : jobError || !job ? (
          <div className="flex flex-1 flex-col items-center justify-center p-8 text-center text-neutral-500">
            <p className="mb-2 text-xs font-medium text-red-500">
              Failed to retrieve job details.
            </p>
            <button
              onClick={closeJob}
              type="button"
              className="rounded-lg bg-neutral-100 px-3 py-1.5 text-xs font-semibold text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300"
            >
              Return to Grid
            </button>
          </div>
        ) : (
          /* Main Scrollable Drawer Content Container */
          <div
            id="drawer-scroll-container"
            className="no-scrollbar flex-1 space-y-6 overflow-y-auto p-5"
          >
            {/* 1. Header Hero section */}
            <div className="flex items-start gap-4">
              <div className="flex size-14 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-neutral-100 bg-white shadow-sm dark:border-neutral-900">
                {job.company_logo_url ? (
                  <img
                    src={job.company_logo_url}
                    alt={job.company_name}
                    className="h-full w-full object-cover"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <div
                    className={`flex h-full w-full items-center justify-center text-lg font-bold ${fallbackColorStyle}`}
                  >
                    {job.company_name.charAt(0).toUpperCase()}
                  </div>
                )}
              </div>

              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <h4 className="truncate text-xs font-bold tracking-tight text-neutral-500 dark:text-neutral-400">
                    {job.company_name}
                  </h4>
                  {company?.ats_type && (
                    <span className="inline-flex rounded border border-cyan-100 bg-cyan-50 px-1.5 py-0.5 text-[9px] font-extrabold tracking-wider text-cyan-700 uppercase dark:border-cyan-900/40 dark:bg-cyan-950/30 dark:text-cyan-400">
                      via {company.ats_type}
                    </span>
                  )}
                </div>

                <h2 className="text-lg leading-snug font-bold tracking-tight text-neutral-800 dark:text-neutral-100">
                  {job.title}
                </h2>

                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 pt-0.5 text-xs text-neutral-500">
                  <span className="flex items-center gap-0.5">
                    <MapPin className="size-3.5" />
                    <span>{job.location_display || job.city}</span>
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-0.5">
                    <Calendar className="size-3.5" />
                    <span>Posted {formatRelativeTime(job.posted_at)}</span>
                  </span>
                </div>
              </div>
            </div>

            <hr className="border-neutral-100 dark:border-neutral-950" />

            {/* 2. Key Fact Sheet grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1 rounded-xl border border-neutral-100/60 bg-neutral-50/50 p-3 dark:border-neutral-900/40 dark:bg-neutral-900/35">
                <span className="flex items-center gap-1.5 text-[10px] font-bold tracking-widest text-neutral-400 uppercase">
                  <Award className="size-3.5 text-indigo-500" />
                  <span>Seniority</span>
                </span>
                <p className="text-xs font-bold text-neutral-700 capitalize dark:text-neutral-200">
                  {job.seniority || "Unspecified"}
                </p>
              </div>

              <div className="space-y-1 rounded-xl border border-neutral-100/60 bg-neutral-50/50 p-3 dark:border-neutral-900/40 dark:bg-neutral-900/35">
                <span className="flex items-center gap-1.5 text-[10px] font-bold tracking-widest text-neutral-400 uppercase">
                  <Briefcase className="size-3.5 text-pink-500" />
                  <span>Category</span>
                </span>
                <p className="text-xs font-bold text-neutral-700 capitalize dark:text-neutral-200">
                  {job.role_category || "General"}
                </p>
              </div>

              <div className="space-y-1 rounded-xl border border-neutral-100/60 bg-neutral-50/50 p-3 dark:border-neutral-900/40 dark:bg-neutral-900/35">
                <span className="flex items-center gap-1.5 text-[10px] font-bold tracking-widest text-neutral-400 uppercase">
                  <Globe className="size-3.5 text-emerald-500" />
                  <span>Remote Mode</span>
                </span>
                <p className="text-xs font-bold text-neutral-700 capitalize dark:text-neutral-200">
                  {job.remote_type ? job.remote_type.replace("-", " ") : "N/A"}
                </p>
              </div>

              <div className="space-y-1 rounded-xl border border-neutral-100/60 bg-neutral-50/50 p-3 dark:border-neutral-900/40 dark:bg-neutral-900/35">
                <span className="flex items-center gap-1.5 text-[10px] font-bold tracking-widest text-neutral-400 uppercase">
                  <Clock className="size-3.5 text-amber-500" />
                  <span>Job Type</span>
                </span>
                <p className="text-xs font-bold text-neutral-700 capitalize dark:text-neutral-200">
                  {job.is_remote ? "Fully Remote" : "Onsite / Hybrid"}
                </p>
              </div>
            </div>

            {/* 3. Tech stack tag row */}
            {job.tech_stack && job.tech_stack.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-bold tracking-wider text-neutral-400 uppercase">
                  Target Tech Stack
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {job.tech_stack.map((tech) => (
                    <span
                      key={tech}
                      className="rounded-lg border border-neutral-200/55 bg-neutral-100 px-2.5 py-1 text-xs font-semibold text-neutral-700 transition-transform hover:scale-103 dark:border-neutral-800/80 dark:bg-neutral-900 dark:text-neutral-300"
                    >
                      {tech}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <hr className="border-neutral-100 dark:border-neutral-950" />

            {/* 4. Full HTML Description */}
            <div className="space-y-2.5">
              <h4 className="text-xs font-bold tracking-wider text-neutral-400 uppercase">
                Position Overview
              </h4>
              <div
                className={`prose-compact space-y-4 overflow-hidden text-sm leading-relaxed text-neutral-700 transition-all dark:text-neutral-300 ${
                  descExpanded ? "h-auto" : "relative max-h-[300px]"
                }`}
              >
                <div
                  dangerouslySetInnerHTML={{ __html: sanitizedDescription }}
                  className="prose-ul:list-disc prose-ul:pl-4 prose-ol:list-decimal prose-ol:pl-4 prose-h3:font-bold prose-h3:mt-3 prose-h3:mb-1 space-y-3"
                />
                {!descExpanded && (
                  /* Ambient gradient overlay to hide text */
                  <div className="pointer-events-none absolute right-0 bottom-0 left-0 h-20 bg-gradient-to-t from-white to-transparent dark:from-neutral-950" />
                )}
              </div>

              <button
                id="btn-toggle-desc-size"
                onClick={() => setDescExpanded(!descExpanded)}
                type="button"
                className="flex items-center gap-1.5 text-xs font-extrabold text-indigo-600 outline-none hover:underline dark:text-indigo-400"
              >
                {descExpanded ? (
                  <>
                    <span>Show Less</span>
                    <ChevronUp className="size-3.5" />
                  </>
                ) : (
                  <>
                    <span>Read Full Overview</span>
                    <ChevronDown className="size-3.5" />
                  </>
                )}
              </button>
            </div>

            <hr className="border-neutral-100 dark:border-neutral-950" />

            {/* 5. Company Card and Bio details */}
            {company && (
              <div className="space-y-3.5 rounded-xl border border-neutral-200 bg-neutral-50/40 p-4 dark:border-neutral-900 dark:bg-neutral-900/20">
                <div className="flex items-center gap-3">
                  <div className="flex size-11 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-xs dark:border-neutral-800">
                    {company.logo_url ? (
                      <img
                        src={company.logo_url}
                        alt={company.name}
                        className="h-full w-full object-cover"
                        referrerPolicy="no-referrer"
                      />
                    ) : (
                      <div
                        className={`flex h-full w-full items-center justify-center text-sm font-bold ${fallbackColorStyle}`}
                      >
                        {company.name.charAt(0).toUpperCase()}
                      </div>
                    )}
                  </div>
                  <div>
                    <h5 className="text-sm leading-none font-bold text-neutral-800 dark:text-neutral-100">
                      {company.name}
                    </h5>
                    <a
                      href={company.website ?? undefined}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 inline-flex max-w-[200px] items-center gap-0.5 truncate text-xs text-indigo-600 hover:underline dark:text-indigo-400"
                    >
                      <span>Visit website</span>
                      <ExternalLink className="size-2.5" />
                    </a>
                  </div>
                </div>

                {/* Company specifications block */}
                <div className="flex flex-wrap gap-1.5">
                  {company.stage && (
                    <span className="rounded border border-neutral-200/40 bg-neutral-100/60 px-2 py-0.5 text-[10px] font-bold tracking-wider text-neutral-600 uppercase dark:border-neutral-700/50 dark:bg-neutral-800 dark:text-neutral-400">
                      {company.stage}
                    </span>
                  )}
                  {company.industry?.slice(0, 3).map((ind) => (
                    <span
                      key={ind}
                      className="rounded border border-neutral-200/40 bg-neutral-100/60 px-2 py-0.5 text-[10px] font-bold tracking-wider text-neutral-600 uppercase dark:border-neutral-700/50 dark:bg-neutral-800 dark:text-neutral-400"
                    >
                      {ind}
                    </span>
                  ))}
                </div>

                <p className="line-clamp-3 text-xs leading-relaxed text-neutral-500 dark:text-neutral-400">
                  {company.description}
                </p>
              </div>
            )}

            {/* 6. Horizontally scrolling other listings card list row */}
            {relatedJobs && relatedJobs.length > 1 && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold tracking-wider text-neutral-400 uppercase">
                  More openings from {job.company_name}
                </h4>

                <div className="no-scrollbar flex shrink-0 scrollbar-thin scrollbar-thumb-neutral-200 scrollbar-track-transparent gap-3 overflow-x-auto pb-2">
                  {relatedJobs
                    .filter((item) => item.id !== job.id)
                    .slice(0, 5)
                    .map((item) => (
                      <div
                        key={item.id}
                        onClick={() => openJob(item.id)}
                        className="w-[200px] shrink-0 cursor-pointer rounded-xl border border-neutral-200 bg-white p-3.5 shadow-xs transition-all hover:border-indigo-500/50 active:scale-98 dark:border-neutral-900 dark:bg-neutral-900 dark:hover:border-indigo-400/50"
                      >
                        <h6 className="truncate text-xs font-semibold text-neutral-400">
                          {item.company_name}
                        </h6>
                        <h5 className="mt-0.5 truncate text-xs leading-snug font-bold text-neutral-800 dark:text-neutral-200">
                          {item.title}
                        </h5>
                        <p className="mt-1 text-[10px] text-neutral-500">
                          {item.location_display || item.city}
                        </p>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
