import {
  Briefcase,
  ChevronLeft,
  ExternalLink,
  Loader2,
  MapPin,
} from "lucide-react";
import type { CompanyDetail, Job } from "../types";
import { CompanyAvatar } from "./CompanyAvatar";
import { JobCard } from "./JobCard";

type Props = {
  company: CompanyDetail | null;
  loading: boolean;
  jobs: Job[];
  jobsLoading: boolean;
  nextCursor: string | null;
  loadingMore: boolean;
  onLoadMore: () => void;
  onJobClick: (id: string) => void;
  onBack: () => void;
};

export function CompanyDetailView({
  company,
  loading,
  jobs,
  jobsLoading,
  nextCursor,
  loadingMore,
  onLoadMore,
  onJobClick,
  onBack,
}: Props) {
  if (loading || !company) {
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
          aria-label="Back to companies"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="truncate text-[11px] text-gray-400">Companies</span>
      </div>

      <div className="no-scrollbar flex flex-1 flex-col overflow-y-auto">
        <div className="flex flex-col gap-3 border-b border-black/8 p-3">
          <div className="flex items-start gap-3">
            <CompanyAvatar
              name={company.name}
              slug={company.slug}
              logoUrl={company.logo_url}
              size={44}
            />
            <div className="min-w-0 flex-1">
              <h3 className="text-sm leading-snug font-semibold text-gray-900">
                {company.name}
              </h3>
              {(company.city || company.country_code) && (
                <p className="mt-0.5 flex items-center gap-1 text-[11px] text-gray-400">
                  <MapPin className="h-2.5 w-2.5 shrink-0" />
                  {[company.city, company.country_code]
                    .filter(Boolean)
                    .join(", ")}
                </p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {company.stage && (
              <span className="rounded-full border border-black/8 bg-white/60 px-2 py-1 text-[11px] text-gray-600 capitalize">
                {company.stage}
              </span>
            )}
            {company.founded_year && (
              <span className="rounded-full border border-black/8 bg-white/60 px-2 py-1 text-[11px] text-gray-600">
                Est. {company.founded_year}
              </span>
            )}
            {company.industry.map((ind) => (
              <span
                key={ind}
                className="rounded-full border border-black/8 bg-white/60 px-2 py-1 text-[11px] text-gray-600 capitalize"
              >
                {ind}
              </span>
            ))}
            <span className="flex items-center gap-1 rounded-full border border-black/8 bg-white/60 px-2 py-1 text-[11px] text-gray-600">
              <Briefcase className="h-2.5 w-2.5" />
              {company.job_count} open role{company.job_count !== 1 ? "s" : ""}
            </span>
          </div>

          {company.open_role_categories.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {company.open_role_categories.map((cat) => (
                <span
                  key={cat}
                  className="rounded-md bg-green-50 px-1.5 py-0.5 text-[10px] font-medium text-green-700 capitalize"
                >
                  {cat}
                </span>
              ))}
            </div>
          )}

          {company.description && (
            <p className="line-clamp-3 text-[12px] leading-relaxed text-gray-600">
              {company.description}
            </p>
          )}

          {company.website && (
            <a
              href={company.website}
              target="_blank"
              rel="noopener noreferrer"
              className="flex w-fit items-center gap-1 rounded-lg border border-black/10 bg-white px-2.5 py-1.5 text-[11px] font-medium text-gray-600 transition-colors hover:bg-black hover:text-white"
            >
              <ExternalLink className="h-3 w-3" />
              Visit website
            </a>
          )}
        </div>

        <div className="flex flex-col">
          <div className="border-b border-black/8 px-3 py-2">
            <p className="text-[10px] font-medium tracking-widest text-gray-400 uppercase">
              Open roles
            </p>
          </div>

          {jobsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-gray-300" />
            </div>
          ) : jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-1 py-8 text-center">
              <p className="text-sm text-gray-400">No open roles</p>
            </div>
          ) : (
            <div className="flex flex-col py-1">
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  onClick={() => onJobClick(job.id)}
                />
              ))}
              {nextCursor && (
                <button
                  onClick={onLoadMore}
                  disabled={loadingMore}
                  className="mx-3 mt-1 mb-2 flex items-center justify-center gap-1.5 rounded-lg border border-black/8 py-2 text-xs text-gray-500 transition-colors hover:bg-black/5 disabled:opacity-50"
                >
                  {loadingMore ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    "Load more"
                  )}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
