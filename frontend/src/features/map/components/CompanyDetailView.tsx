import { SocialIcon } from "@/components/ui/social-icons";
import {
  Briefcase,
  Building2,
  Calendar,
  ChevronLeft,
  DollarSign,
  FileText,
  Globe,
  Laptop,
  Loader2,
  MapPin,
  Tag,
  TrendingUp,
  User,
  Users,
} from "lucide-react";
import { useState } from "react";
import type { CompanyDetail, Job } from "../types";
import { CompanyAvatar } from "./CompanyAvatar";
import { JobCard } from "./JobCard";

type Founder = {
  name: string;
  title: string | null;
  twitter_url: string | null;
  linkedin_url: string | null;
  photo_url: string | null;
};

type Investor = {
  name: string;
  logo_url: string | null;
};

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

function formatFunding(usd: number): string {
  if (usd >= 1_000_000_000) return `$${(usd / 1_000_000_000).toFixed(1)}B`;
  if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(0)}M`;
  if (usd >= 1_000) return `$${(usd / 1_000).toFixed(0)}K`;
  return `$${usd}`;
}

function castFounder(raw: Record<string, unknown>): Founder {
  return {
    name: String(raw.name ?? ""),
    title: raw.title != null ? String(raw.title) : null,
    twitter_url: raw.twitter_url != null ? String(raw.twitter_url) : null,
    linkedin_url: raw.linkedin_url != null ? String(raw.linkedin_url) : null,
    photo_url: raw.photo_url != null ? String(raw.photo_url) : null,
  };
}

function castInvestor(raw: Record<string, unknown>): Investor {
  return {
    name: String(raw.name ?? ""),
    logo_url: raw.logo_url != null ? String(raw.logo_url) : null,
  };
}

function MetaRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex gap-2">
      <span className="mt-px shrink-0 text-gray-400">{icon}</span>
      <p className="text-[11px] leading-snug text-gray-600">
        <span className="text-gray-400">{label}:</span> {value}
      </p>
    </div>
  );
}

function FounderCard({ founder }: { founder: Founder }) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-black/8 bg-gray-50/60 p-2.5">
      {founder.photo_url ? (
        <img
          src={founder.photo_url}
          alt={founder.name}
          className="h-8 w-8 shrink-0 rounded-full bg-gray-100 object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      ) : (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-200 text-xs font-medium text-gray-600">
          {founder.name.charAt(0).toUpperCase()}
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-semibold text-gray-900">
          {founder.name}
        </p>
        {founder.title && (
          <p className="text-[10px] text-gray-400 capitalize">
            {founder.title}
          </p>
        )}
      </div>
      <div className="flex shrink-0 gap-1">
        {founder.linkedin_url && (
          <a
            href={founder.linkedin_url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`${founder.name} on LinkedIn`}
            className="flex h-6 w-6 items-center justify-center rounded border border-black/8 bg-white text-gray-400 transition-colors hover:bg-black hover:text-white"
          >
            <SocialIcon platform="linkedin" className="h-3 w-3" />
          </a>
        )}
        {founder.twitter_url && (
          <a
            href={founder.twitter_url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`${founder.name} on X`}
            className="flex h-6 w-6 items-center justify-center rounded border border-black/8 bg-white text-gray-400 transition-colors hover:bg-black hover:text-white"
          >
            <SocialIcon platform="x" className="h-3 w-3" />
          </a>
        )}
      </div>
    </div>
  );
}

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
  const [descExpanded, setDescExpanded] = useState(false);

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

  const founders: Founder[] = (company.founders ?? [])
    .map(castFounder)
    .filter((f) => f.name);

  const investors: Investor[] = (company.key_investors ?? [])
    .map(castInvestor)
    .filter((i) => i.name);

  const KNOWN_PLATFORMS = new Set([
    "twitter",
    "x",
    "linkedin",
    "instagram",
    "github",
    "facebook",
  ]);
  const socialEntries = company.social_links
    ? Object.entries(company.social_links).filter(
        ([platform, url]) =>
          !!url && KNOWN_PLATFORMS.has(platform.toLowerCase()),
      )
    : [];

  const location = [company.city, company.country_code]
    .filter(Boolean)
    .join(", ");

  const fundingStageLabel = company.funding_stage ?? company.stage ?? null;

  const hasMetadata =
    company.industry.length > 0 ||
    !!company.business_model ||
    !!company.founded_year ||
    company.work_modes.length > 0 ||
    !!company.headcount_range ||
    company.departments.length > 0 ||
    !!company.office_address ||
    !!fundingStageLabel ||
    !!company.total_funding_usd;

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
          <div className="flex items-center gap-3">
            <CompanyAvatar
              name={company.name}
              logoUrl={company.logo_url}
              size={44}
            />
            <div className="min-w-0">
              <h3 className="text-sm leading-snug font-semibold text-gray-900">
                {company.name}
              </h3>
              {location && (
                <p className="mt-0.5 text-[11px] text-gray-400">{location}</p>
              )}
            </div>
          </div>

          {(company.website || socialEntries.length > 0) && (
            <div className="flex flex-wrap gap-1.5">
              {company.website && (
                <a
                  href={company.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Website"
                  className="flex h-7 w-7 items-center justify-center rounded-lg border border-black/8 bg-white text-gray-500 transition-colors hover:bg-black hover:text-white"
                >
                  <Globe className="h-3.5 w-3.5" />
                </a>
              )}
              {socialEntries.map(([platform, url]) => (
                <a
                  key={platform}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={platform}
                  className="flex h-7 w-7 items-center justify-center rounded-lg border border-black/8 bg-white text-gray-500 transition-colors hover:bg-black hover:text-white"
                >
                  <SocialIcon
                    platform={platform.toLowerCase()}
                    className="h-3.5 w-3.5"
                  />
                </a>
              ))}
            </div>
          )}
        </div>

        {hasMetadata && (
          <div className="flex flex-col gap-2 border-b border-black/8 px-3 py-3">
            {company.industry.length > 0 && (
              <MetaRow
                icon={<Tag className="h-3 w-3" />}
                label="Industry"
                value={
                  company.industry.filter(Boolean).join(", ") || "Not available"
                }
              />
            )}
            {company.business_model && (
              <MetaRow
                icon={<Briefcase className="h-3 w-3" />}
                label="Business model"
                value={company.business_model}
              />
            )}
            {company.founded_year && (
              <MetaRow
                icon={<Calendar className="h-3 w-3" />}
                label="Founded"
                value={String(company.founded_year)}
              />
            )}
            {company.work_modes.length > 0 && (
              <MetaRow
                icon={<Laptop className="h-3 w-3" />}
                label="Work mode"
                value={
                  company.work_modes.filter(Boolean).join(", ") ||
                  "Not available"
                }
              />
            )}
            {company.headcount_range && (
              <MetaRow
                icon={<Users className="h-3 w-3" />}
                label="Team size"
                value={company.headcount_range}
              />
            )}
            {company.departments.length > 0 && (
              <MetaRow
                icon={<Building2 className="h-3 w-3" />}
                label="Departments"
                value={
                  company.departments.filter(Boolean).join(", ") ||
                  "Not available"
                }
              />
            )}
            {company.office_address && (
              <MetaRow
                icon={<MapPin className="h-3 w-3" />}
                label="HQ"
                value={company.office_address}
              />
            )}
            {fundingStageLabel && (
              <MetaRow
                icon={<TrendingUp className="h-3 w-3" />}
                label="Funding stage"
                value={fundingStageLabel}
              />
            )}
            {company.total_funding_usd && (
              <MetaRow
                icon={<DollarSign className="h-3 w-3" />}
                label="Total funding"
                value={formatFunding(company.total_funding_usd)}
              />
            )}
          </div>
        )}

        {company.description && (
          <div className="flex flex-col gap-1.5 border-b border-black/8 px-3 py-3">
            <div className="flex items-center gap-2">
              <FileText className="h-3 w-3 shrink-0 text-gray-400" />
              <span className="text-[11px] text-gray-400">About</span>
            </div>
            <p
              className={`text-[11px] leading-relaxed text-gray-600 ${
                !descExpanded ? "line-clamp-4" : ""
              }`}
            >
              {company.description}
            </p>
            {company.description.length > 180 && (
              <button
                onClick={() => setDescExpanded((prev) => !prev)}
                className="self-start text-[10px] font-medium text-gray-500 hover:text-gray-700"
              >
                {descExpanded ? "Show less" : "Show more"}
              </button>
            )}
          </div>
        )}

        {founders.length > 0 && (
          <div className="flex flex-col gap-2 border-b border-black/8 px-3 py-3">
            <div className="flex items-center gap-2">
              <User className="h-3 w-3 shrink-0 text-gray-400" />
              <span className="text-[11px] text-gray-400">
                Founders ({founders.length})
              </span>
            </div>
            <div className="flex flex-col gap-1.5">
              {founders.map((f) => (
                <FounderCard key={f.name} founder={f} />
              ))}
            </div>
          </div>
        )}

        {investors.length > 0 && (
          <div className="flex flex-col gap-1.5 border-b border-black/8 px-3 py-3">
            <div className="flex items-center gap-2">
              <DollarSign className="h-3 w-3 shrink-0 text-gray-400" />
              <span className="text-[11px] text-gray-400">Key investors</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {investors.map((inv) => (
                <span
                  key={inv.name}
                  className="rounded-full border border-black/8 bg-gray-50 px-2 py-0.5 text-[10px] text-gray-600"
                >
                  {inv.name}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-col">
          <div className="border-b border-black/8 px-3 py-2">
            <div className="flex items-center gap-2">
              <Briefcase className="h-3 w-3 text-gray-400" />
              <span className="text-[11px] text-gray-400">
                Open positions
                {company.job_count > 0 ? ` (${company.job_count})` : ""}
              </span>
            </div>
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
