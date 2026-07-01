import { relativeTime } from "@/lib/utils";
import type { Job } from "@/types";
import { CompanyAvatar } from "./CompanyAvatar";

type Props = {
  job: Job;
  onClick: () => void;
};

export function JobCard({ job, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="w-full rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-black/5 focus-visible:ring-2 focus-visible:ring-black/20 focus-visible:outline-none"
    >
      <div className="flex items-start gap-2.5">
        <CompanyAvatar
          name={job.company_name}
          logoUrl={job.company_logo_url}
          size={28}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-1">
            <p className="truncate text-[11px] text-gray-400">
              {job.company_name}
            </p>
            {job.posted_at && (
              <span className="shrink-0 text-[10px] text-gray-400">
                {relativeTime(job.posted_at)}
              </span>
            )}
          </div>
          <p className="mt-0.5 line-clamp-2 text-sm leading-snug font-medium text-gray-900">
            {job.title}
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1">
            {job.location_display && (
              <span className="text-[10px] text-gray-400">
                {job.location_display}
              </span>
            )}
            {job.seniority && (
              <span className="rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 capitalize">
                {job.seniority}
              </span>
            )}
            {job.is_remote && (
              <span className="rounded-full bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600 capitalize">
                {job.remote_type === "hybrid" ? "Hybrid" : "Remote"}
              </span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}
