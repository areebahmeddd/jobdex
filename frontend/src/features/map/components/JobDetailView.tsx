import { ChevronLeft, ExternalLink, Loader2, MapPin } from "lucide-react";
import type { JobDetail } from "../types";
import { relativeTime } from "../utils";
import { CompanyAvatar } from "./CompanyAvatar";

type Props = {
  job: JobDetail | null;
  loading: boolean;
  onBack: () => void;
};

export function JobDetailView({ job, loading, onBack }: Props) {
  if (loading || !job) {
    return (
      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="flex shrink-0 items-center gap-2 border-b border-black/8 px-3 py-2">
          <button
            onClick={onBack}
            className="flex h-7 w-7 items-center justify-center rounded-full text-gray-400 hover:bg-black/5 hover:text-gray-700"
            aria-label="Back"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-xs text-gray-400">Loading...</span>
        </div>
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-gray-300" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center gap-2 border-b border-black/8 px-3 py-2">
        <button
          onClick={onBack}
          className="flex h-7 w-7 items-center justify-center rounded-full text-gray-400 hover:bg-black/5 hover:text-gray-700"
          aria-label="Back to results"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="truncate text-[11px] text-gray-400">
          {job.company_name}
        </span>
      </div>

      <div className="no-scrollbar flex flex-1 flex-col gap-3 overflow-y-auto p-3">
        <div className="flex items-start gap-3">
          <CompanyAvatar
            name={job.company_name}
            slug={job.company_slug}
            logoUrl={job.company_logo_url}
            size={40}
          />
          <div className="min-w-0 flex-1">
            <p className="text-[11px] text-gray-400">{job.company_name}</p>
            <h3 className="mt-0.5 text-sm leading-snug font-semibold text-gray-900">
              {job.title}
            </h3>
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {job.location_display && (
            <span className="flex items-center gap-1 rounded-full border border-black/8 bg-white/60 px-2 py-1 text-[11px] text-gray-600">
              <MapPin className="h-2.5 w-2.5" />
              {job.location_display}
            </span>
          )}
          {job.seniority && (
            <span className="rounded-full border border-black/8 bg-white/60 px-2 py-1 text-[11px] text-gray-600 capitalize">
              {job.seniority}
            </span>
          )}
          {job.is_remote && (
            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-[11px] text-emerald-600">
              Remote OK
            </span>
          )}
          {job.role_category && (
            <span className="rounded-full border border-black/8 bg-white/60 px-2 py-1 text-[11px] text-gray-600 capitalize">
              {job.role_category}
            </span>
          )}
        </div>

        {job.description_snippet && (
          <p className="line-clamp-6 text-[12px] leading-relaxed text-gray-600">
            {job.description_snippet}
          </p>
        )}

        {job.tech_stack && job.tech_stack.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {job.tech_stack.slice(0, 10).map((tech) => (
              <span
                key={tech}
                className="rounded-md bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-600"
              >
                {tech}
              </span>
            ))}
          </div>
        )}

        {job.posted_at && (
          <p className="text-[11px] text-gray-400">
            Posted {relativeTime(job.posted_at)}
          </p>
        )}

        <a
          href={job.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-auto flex items-center justify-center gap-1.5 rounded-lg bg-gray-400 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-gray-500"
        >
          Apply
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </div>
    </div>
  );
}
