import type { PanelMode } from "@/features/map/hooks/useJobFilters";
import type { SortValue } from "@/lib/filters";
import type {
  CompanyDetail,
  CompanyListItem,
  Job,
  JobDetail,
  PanelView,
} from "@/types";
import { ChevronDown, Loader2, SearchX } from "lucide-react";
import { CompanyCard } from "./CompanyCard";
import { CompanyDetailView } from "./CompanyDetailView";
import { DefaultPanel } from "./DefaultPanel";
import { JobCard } from "./JobCard";
import { JobDetailView } from "./JobDetailView";
import { ResultsToolbar } from "./ResultsToolbar";

type Props = {
  open: boolean;
  onToggle: () => void;
  showHint?: boolean;
  view: PanelView;
  mode: PanelMode;
  onModeChange: (mode: PanelMode) => void;
  selectedCity: string | null;
  total: number | null;
  sort: SortValue;
  onSortChange: (sort: SortValue) => void;
  hasQuery: boolean;
  hasFilters: boolean;
  onClearFilters: () => void;
  onSearchEverywhere: () => void;
  companies: CompanyListItem[];
  companiesLoading: boolean;
  onCompanyClick: (slug: string) => void;
  selectedCompany: CompanyDetail | null;
  selectedCompanyLoading: boolean;
  selectedCompanyFailed: boolean;
  jobs: Job[];
  jobsLoading: boolean;
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
  onJobClick: (id: string) => void;
  jobDetail: JobDetail | null;
  jobDetailLoading: boolean;
  jobDetailFailed: boolean;
  onBack: () => void;
};

function panelLabel(view: PanelView): string {
  if (view === "job-detail") return "Job detail";
  if (view === "jobs") return "Results";
  if (view === "companies") return "Companies";
  if (view === "company-detail") return "Company";
  return "Explore";
}

function EmptyResults({
  noun,
  selectedCity,
  hasFilters,
  onClearFilters,
  onSearchEverywhere,
}: {
  noun: string;
  selectedCity: string | null;
  hasFilters: boolean;
  onClearFilters: () => void;
  onSearchEverywhere: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 text-center">
      <SearchX className="h-5 w-5 text-gray-300" aria-hidden="true" />
      <div>
        <p className="text-sm font-medium text-gray-700">No {noun} found</p>
        <p className="mt-1 text-xs text-gray-500">
          Nothing matches this combination of filters.
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-1.5">
        {hasFilters && (
          <button
            type="button"
            onClick={onClearFilters}
            className="rounded-full bg-black px-3 py-1.5 text-[11px] font-medium text-white transition-colors hover:bg-gray-800"
          >
            Clear filters
          </button>
        )}
        {selectedCity && (
          <button
            type="button"
            onClick={onSearchEverywhere}
            className="rounded-full border border-black/10 bg-white px-3 py-1.5 text-[11px] font-medium text-gray-700 transition-colors hover:bg-black/5"
          >
            Search everywhere
          </button>
        )}
      </div>
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="flex flex-1 items-center justify-center">
      <Loader2 className="h-5 w-5 animate-spin text-gray-300" />
    </div>
  );
}

export function ResultsPanel({
  open,
  onToggle,
  showHint,
  view,
  mode,
  onModeChange,
  selectedCity,
  total,
  sort,
  onSortChange,
  hasQuery,
  hasFilters,
  onClearFilters,
  onSearchEverywhere,
  companies,
  companiesLoading,
  onCompanyClick,
  selectedCompany,
  selectedCompanyLoading,
  selectedCompanyFailed,
  jobs,
  jobsLoading,
  hasMore,
  loadingMore,
  onLoadMore,
  onJobClick,
  jobDetail,
  jobDetailLoading,
  jobDetailFailed,
  onBack,
}: Props) {
  const isList = view === "jobs" || view === "companies";
  const listLoading = view === "jobs" ? jobsLoading : companiesLoading;

  return (
    <aside
      className={`absolute right-4 bottom-4 left-4 z-[1000] flex flex-col overflow-hidden rounded-2xl border border-white/20 bg-white/25 shadow-sm shadow-black/5 backdrop-blur-md transition-[height] duration-300 ease-in-out sm:inset-auto sm:top-4 sm:right-4 sm:w-72 ${open ? "h-72 sm:h-[calc(100%-2rem)]" : "h-12"}`}
    >
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-white/20 px-3">
        <span className="truncate text-xs font-medium tracking-widest text-gray-500 uppercase">
          {panelLabel(view)}
        </span>
        <div className="flex shrink-0 items-center gap-1.5">
          {showHint && !open && (
            <span className="animate-pulse text-[10px] text-gray-400">
              explore
            </span>
          )}
          <button
            aria-label={open ? "Collapse panel" : "Expand panel"}
            aria-expanded={open}
            onClick={onToggle}
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-white/40 hover:text-gray-700"
          >
            <ChevronDown
              className={`h-3.5 w-3.5 transition-transform duration-300 ${open ? "rotate-0" : "rotate-180"} ${showHint && !open ? "animate-bounce" : ""}`}
              aria-hidden="true"
            />
          </button>
        </div>
      </div>

      {open && (
        <div className="flex flex-1 flex-col overflow-hidden">
          {isList && (
            <ResultsToolbar
              mode={mode}
              onModeChange={onModeChange}
              total={total}
              loading={listLoading}
              sort={sort}
              onSortChange={onSortChange}
              hasQuery={hasQuery}
            />
          )}

          {view === "job-detail" && (
            <JobDetailView
              job={jobDetail}
              loading={jobDetailLoading}
              failed={jobDetailFailed}
              onBack={onBack}
            />
          )}

          {view === "company-detail" && (
            <CompanyDetailView
              company={selectedCompany}
              loading={selectedCompanyLoading}
              failed={selectedCompanyFailed}
              jobs={jobs}
              jobsLoading={jobsLoading}
              nextCursor={hasMore ? "more" : null}
              loadingMore={loadingMore}
              onLoadMore={onLoadMore}
              onJobClick={onJobClick}
              onBack={onBack}
            />
          )}

          {view === "companies" &&
            (companiesLoading ? (
              <ListSkeleton />
            ) : companies.length === 0 ? (
              <EmptyResults
                noun="companies"
                selectedCity={selectedCity}
                hasFilters={hasFilters}
                onClearFilters={onClearFilters}
                onSearchEverywhere={onSearchEverywhere}
              />
            ) : (
              <div className="no-scrollbar flex flex-1 flex-col overflow-y-auto py-1">
                {companies.map((co) => (
                  <CompanyCard
                    key={co.id}
                    company={co}
                    onClick={() => onCompanyClick(co.slug)}
                  />
                ))}
              </div>
            ))}

          {view === "jobs" &&
            (jobsLoading ? (
              <ListSkeleton />
            ) : jobs.length === 0 ? (
              <EmptyResults
                noun="jobs"
                selectedCity={selectedCity}
                hasFilters={hasFilters}
                onClearFilters={onClearFilters}
                onSearchEverywhere={onSearchEverywhere}
              />
            ) : (
              <div className="no-scrollbar flex flex-1 flex-col overflow-y-auto py-1">
                {jobs.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    onClick={() => onJobClick(job.id)}
                  />
                ))}
                {hasMore && (
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
            ))}

          {view === "default" && <DefaultPanel />}
        </div>
      )}
    </aside>
  );
}
