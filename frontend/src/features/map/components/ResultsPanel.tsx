import type {
  CompanyDetail,
  CompanyListItem,
  Job,
  JobDetail,
  PanelView,
} from "@/types";
import { ChevronDown, Loader2, MapPin, Search, X } from "lucide-react";
import { CompanyCard } from "./CompanyCard";
import { CompanyDetailView } from "./CompanyDetailView";
import { DefaultPanel } from "./DefaultPanel";
import { JobCard } from "./JobCard";
import { JobDetailView } from "./JobDetailView";

type Props = {
  open: boolean;
  onToggle: () => void;
  view: PanelView;
  selectedCity: string | null;
  onClearCity: () => void;
  companies: CompanyListItem[];
  companiesLoading: boolean;
  onCompanyClick: (slug: string) => void;
  selectedCompany: CompanyDetail | null;
  selectedCompanyLoading: boolean;
  jobs: Job[];
  jobsLoading: boolean;
  nextCursor: string | null;
  loadingMore: boolean;
  onLoadMore: () => void;
  onJobClick: (id: string) => void;
  jobDetail: JobDetail | null;
  jobDetailLoading: boolean;
  onBack: () => void;
};

function panelLabel(view: PanelView): string {
  if (view === "job-detail") return "Job detail";
  if (view === "jobs") return "Results";
  if (view === "companies") return "Companies";
  if (view === "company-detail") return "Company";
  return "Explore";
}

function JobsList({
  selectedCity,
  onClearCity,
  jobs,
  jobsLoading,
  nextCursor,
  loadingMore,
  onLoadMore,
  onJobClick,
}: Pick<
  Props,
  | "selectedCity"
  | "onClearCity"
  | "jobs"
  | "jobsLoading"
  | "nextCursor"
  | "loadingMore"
  | "onLoadMore"
  | "onJobClick"
>) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center gap-2 border-b border-black/8 px-3 py-2">
        {selectedCity ? (
          <>
            <MapPin className="h-3 w-3 shrink-0 text-gray-400" />
            <span className="flex-1 truncate text-xs font-medium text-gray-700">
              {selectedCity}
            </span>
            <button
              onClick={onClearCity}
              className="flex h-5 w-5 items-center justify-center rounded-full text-gray-400 hover:bg-black/5 hover:text-gray-600"
              aria-label="Clear city"
            >
              <X className="h-3 w-3" />
            </button>
          </>
        ) : (
          <>
            <Search className="h-3 w-3 shrink-0 text-gray-400" />
            <span className="flex-1 truncate text-xs font-medium text-gray-700">
              Search results
            </span>
          </>
        )}
      </div>

      {jobsLoading ? (
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-gray-300" />
        </div>
      ) : jobs.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 text-center">
          <p className="text-sm text-gray-400">No jobs found</p>
          {selectedCity && (
            <p className="text-xs text-gray-400">
              Try adjusting filters or searching globally
            </p>
          )}
        </div>
      ) : (
        <div className="no-scrollbar flex flex-1 flex-col overflow-y-auto py-1">
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
  );
}

function CompaniesList({
  selectedCity,
  onClearCity,
  companies,
  companiesLoading,
  onCompanyClick,
}: Pick<
  Props,
  | "selectedCity"
  | "onClearCity"
  | "companies"
  | "companiesLoading"
  | "onCompanyClick"
>) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center gap-2 border-b border-black/8 px-3 py-2">
        <MapPin className="h-3 w-3 shrink-0 text-gray-400" />
        <span className="flex-1 truncate text-xs font-medium text-gray-700">
          {selectedCity ?? "All companies"}
        </span>
        {selectedCity && (
          <button
            onClick={onClearCity}
            className="flex h-5 w-5 items-center justify-center rounded-full text-gray-400 hover:bg-black/5 hover:text-gray-600"
            aria-label="Clear city"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>

      {companiesLoading ? (
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-gray-300" />
        </div>
      ) : companies.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-1 px-4 text-center">
          <p className="text-sm text-gray-400">No companies found</p>
        </div>
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
      )}
    </div>
  );
}

export function ResultsPanel({
  open,
  onToggle,
  view,
  selectedCity,
  onClearCity,
  companies,
  companiesLoading,
  onCompanyClick,
  selectedCompany,
  selectedCompanyLoading,
  jobs,
  jobsLoading,
  nextCursor,
  loadingMore,
  onLoadMore,
  onJobClick,
  jobDetail,
  jobDetailLoading,
  onBack,
}: Props) {
  return (
    <aside
      className={`absolute top-4 right-4 z-[1000] flex w-72 flex-col overflow-hidden rounded-2xl border border-white/20 bg-white/25 shadow-sm shadow-black/5 backdrop-blur-md transition-[height] duration-300 ease-in-out ${
        open ? "h-[calc(100%-2rem)]" : "h-12"
      }`}
    >
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-white/20 px-3">
        <span className="truncate text-xs font-medium tracking-widest text-gray-500 uppercase">
          {panelLabel(view)}
        </span>
        <button
          aria-label={open ? "Collapse panel" : "Expand panel"}
          onClick={onToggle}
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-gray-400 transition-colors hover:bg-white/40 hover:text-gray-700"
        >
          <ChevronDown
            className={`h-3.5 w-3.5 transition-transform duration-300 ${open ? "rotate-0" : "rotate-180"}`}
            aria-hidden="true"
          />
        </button>
      </div>

      {open && (
        <div className="flex flex-1 flex-col overflow-hidden">
          {view === "job-detail" && (
            <JobDetailView
              job={jobDetail}
              loading={jobDetailLoading}
              onBack={onBack}
            />
          )}
          {view === "company-detail" && (
            <CompanyDetailView
              company={selectedCompany}
              loading={selectedCompanyLoading}
              jobs={jobs}
              jobsLoading={jobsLoading}
              nextCursor={nextCursor}
              loadingMore={loadingMore}
              onLoadMore={onLoadMore}
              onJobClick={onJobClick}
              onBack={onBack}
            />
          )}
          {view === "companies" && (
            <CompaniesList
              selectedCity={selectedCity}
              onClearCity={onClearCity}
              companies={companies}
              companiesLoading={companiesLoading}
              onCompanyClick={onCompanyClick}
            />
          )}
          {view === "jobs" && (
            <JobsList
              selectedCity={selectedCity}
              onClearCity={onClearCity}
              jobs={jobs}
              jobsLoading={jobsLoading}
              nextCursor={nextCursor}
              loadingMore={loadingMore}
              onLoadMore={onLoadMore}
              onJobClick={onJobClick}
            />
          )}
          {view === "default" && <DefaultPanel />}
        </div>
      )}
    </aside>
  );
}
