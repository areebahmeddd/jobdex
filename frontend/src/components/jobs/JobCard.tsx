import { ArrowUpRight, Globe, MapPin } from "lucide-react";
import { motion } from "motion/react";
import { useGlobeStore } from "../../lib/store";
import { formatRelativeTime, getSeniorityColor } from "../../lib/utils";
import { Job } from "../../types/api";

interface JobCardProps {
  job: Job;
}

const FALLBACK_PALETTE = [
  "bg-red-500/10 text-red-600 border border-red-500/20 dark:bg-red-950/40 dark:text-red-400 dark:border-red-900/30",
  "bg-blue-500/10 text-blue-600 border border-blue-500/20 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-900/30",
  "bg-green-500/10 text-green-600 border border-green-500/20 dark:bg-green-950/40 dark:text-green-400 dark:border-green-900/30",
  "bg-amber-500/10 text-amber-600 border border-amber-500/20 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-900/30",
  "bg-purple-500/10 text-purple-600 border border-purple-500/20 dark:bg-purple-950/40 dark:text-purple-400 dark:border-purple-900/30",
  "bg-cyan-500/10 text-cyan-600 border border-cyan-500/20 dark:bg-cyan-950/40 dark:text-cyan-400 dark:border-cyan-900/30",
];

export default function JobCard({ job }: JobCardProps) {
  const { openJob, selectedJobId } = useGlobeStore();

  const isSelected = selectedJobId === job.id;

  // Resolve fallbacks for logos
  const charCodeIndex = job.company_name
    ? job.company_name.charCodeAt(0) % 6
    : 0;
  const fallbackColorStyle = FALLBACK_PALETTE[charCodeIndex];

  // Limit tech stacks displayed on list view
  const visibleTech = job.tech_stack ? job.tech_stack.slice(0, 3) : [];
  const excessTechCount = job.tech_stack
    ? Math.max(0, job.tech_stack.length - 3)
    : 0;

  const seniorityStyle = getSeniorityColor(job.seniority);

  const handleCardClick = () => {
    openJob(job.id);
  };

  const handleApplyClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (job.source_url) {
      window.open(job.source_url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <motion.div
      onClick={handleCardClick}
      whileHover={{ y: -3, boxShadow: "0 8px 16px rgba(0,0,0,0.06)" }}
      transition={{ type: "spring", stiffness: 450, damping: 28 }}
      className={`group relative cursor-pointer rounded-xl border p-4 transition-colors select-none ${
        isSelected
          ? "border-indigo-500/60 bg-indigo-50/40 shadow-sm dark:border-indigo-500/40 dark:bg-indigo-950/20"
          : "border-neutral-200 bg-white hover:border-neutral-300 dark:border-neutral-800 dark:bg-neutral-900/65 dark:hover:border-neutral-700"
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Company Logo / Fallback box */}
        <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-lg">
          {job.company_logo_url ? (
            <img
              src={job.company_logo_url}
              alt={`${job.company_name} logo`}
              className="h-full w-full rounded-lg object-cover"
              referrerPolicy="no-referrer"
              onError={(e) => {
                // Fallback on failure
                (e.currentTarget as HTMLImageElement).style.display = "none";
                const container = e.currentTarget.parentElement;
                if (container) {
                  const fallback = document.createElement("div");
                  fallback.className = `w-full h-full rounded-lg flex items-center justify-center font-bold text-sm ${fallbackColorStyle}`;
                  fallback.textContent = job.company_name.charAt(0);
                  container.appendChild(fallback);
                }
              }}
            />
          ) : (
            <div
              className={`flex h-full w-full items-center justify-center rounded-lg text-sm font-bold ${fallbackColorStyle}`}
            >
              {job.company_name
                ? job.company_name.charAt(0).toUpperCase()
                : "J"}
            </div>
          )}
        </div>

        {/* Content Column */}
        <div className="min-w-0 flex-1">
          {/* Company Title Header */}
          <div className="mb-0.5 flex items-center justify-between gap-2">
            <span className="truncate text-xs font-semibold text-neutral-500 dark:text-neutral-400">
              {job.company_name}
            </span>

            {/* Remote specific status badge */}
            {job.is_remote && (
              <span className="inline-flex items-center gap-1 rounded border border-emerald-100 bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700 dark:border-emerald-900/35 dark:bg-emerald-950/30 dark:text-emerald-400">
                <Globe className="size-2.5" />
                <span>Remote</span>
              </span>
            )}
          </div>

          {/* Job Title */}
          <h3 className="mb-1 truncate text-sm leading-snug font-semibold tracking-tight text-neutral-800 transition-colors group-hover:text-indigo-600 dark:text-neutral-100 dark:group-hover:text-indigo-400">
            {job.title}
          </h3>

          {/* Location & Seniority block */}
          <div className="mb-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-neutral-500">
            <span className="flex max-w-[120px] items-center gap-0.5 truncate">
              <MapPin className="size-3 shrink-0" />
              <span>{job.location_display || job.city}</span>
            </span>

            <span className="font-normal text-neutral-300 dark:text-neutral-700">
              •
            </span>

            {job.seniority && (
              <span
                className={`rounded border px-1 text-[10px] font-medium tracking-wide uppercase ${seniorityStyle.bg} ${seniorityStyle.text} ${seniorityStyle.border}`}
              >
                {job.seniority}
              </span>
            )}
          </div>

          {/* Categories and Tech Stack Chips */}
          <div className="mb-2 flex flex-wrap items-center gap-1">
            {job.role_category && (
              <span className="rounded-md border border-indigo-100 bg-indigo-50 px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-indigo-700 uppercase dark:border-indigo-900/30 dark:bg-indigo-950/20 dark:text-indigo-400">
                {job.role_category}
              </span>
            )}

            {visibleTech.map((tech) => (
              <span
                key={tech}
                className="rounded-md border border-neutral-200/50 bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium text-neutral-600 dark:border-neutral-700/50 dark:bg-neutral-800/60 dark:text-neutral-400"
              >
                {tech}
              </span>
            ))}

            {excessTechCount > 0 && (
              <span className="rounded-md bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium text-neutral-500 dark:bg-neutral-800/40">
                +{excessTechCount}
              </span>
            )}
          </div>

          {/* Footer details */}
          <div className="mt-2.5 flex items-center justify-between border-t border-neutral-100 pt-2 text-[10px] text-neutral-400 dark:border-neutral-800">
            <span>Posted {formatRelativeTime(job.posted_at)}</span>

            <button
              onClick={handleApplyClick}
              type="button"
              className="group/btn inline-flex items-center gap-0.5 text-xs font-semibold text-indigo-600 transition-colors hover:text-indigo-700 hover:underline dark:text-indigo-400 dark:hover:text-indigo-300"
            >
              <span>Apply</span>
              <ArrowUpRight className="size-3 transition-transform group-hover/btn:translate-x-0.5 group-hover/btn:-translate-y-0.5" />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
