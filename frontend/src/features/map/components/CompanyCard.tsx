import type { CompanyListItem } from "@/types";
import { Briefcase, ChevronRight } from "lucide-react";
import { CompanyAvatar } from "./CompanyAvatar";

type Props = {
  company: CompanyListItem;
  onClick: () => void;
};

export function CompanyCard({ company, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="group flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-black/5 focus-visible:ring-2 focus-visible:ring-black/20 focus-visible:outline-none"
    >
      <CompanyAvatar name={company.name} logoUrl={company.logo_url} size={32} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-900">
          {company.name}
        </p>
        {company.job_count > 0 && (
          <div className="mt-0.5 flex items-center gap-0.5">
            <span className="flex shrink-0 items-center gap-0.5 text-[11px] text-gray-500">
              <Briefcase className="h-2.5 w-2.5" />
              {company.job_count} open role{company.job_count !== 1 ? "s" : ""}
            </span>
          </div>
        )}
      </div>
      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-gray-300 transition-colors group-hover:text-gray-500" />
    </button>
  );
}
