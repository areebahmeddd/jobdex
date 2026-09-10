export type FilterKey = "source" | "role" | "level" | "type" | "mode";

export type FacetKey =
  "ats_type" | "role_category" | "seniority" | "job_type" | "work_mode";

export type FilterGroup = {
  key: FilterKey;
  param: string;
  facet: FacetKey;
  title: string;
  labels: Record<string, string>;
  order?: readonly string[];
};

const SOURCE_LABELS: Record<string, string> = {
  ashby: "Ashby",
  greenhouse: "Greenhouse",
  lever: "Lever",
  smartrecruiters: "SmartRecruiters",
  workable: "Workable",
  workday: "Workday",
  rippling: "Rippling",
  ycombinator: "Y Combinator",
  recruitee: "Recruitee",
  teamtailor: "Teamtailor",
  pyjamahr: "PyjamaHR",
  mcf: "MyCareersFuture",
};

const ROLE_LABELS: Record<string, string> = {
  engineering: "Engineering",
  data: "Data",
  design: "Design",
  product: "Product",
  marketing: "Marketing",
  sales: "Sales",
  operations: "Operations",
  finance: "Finance",
  legal: "Legal",
  hr: "People & HR",
  support: "Support",
  research: "Research",
  healthcare: "Healthcare",
  hospitality: "Hospitality",
  other: "Other",
};

const LEVEL_LABELS: Record<string, string> = {
  intern: "Intern",
  junior: "Junior",
  mid: "Mid",
  senior: "Senior",
  staff: "Staff",
  lead: "Lead",
  principal: "Principal",
  manager: "Manager",
  director: "Director",
  executive: "Executive",
};

const LEVEL_ORDER = [
  "intern",
  "junior",
  "mid",
  "senior",
  "staff",
  "lead",
  "principal",
  "manager",
  "director",
  "executive",
] as const;

const JOB_TYPE_LABELS: Record<string, string> = {
  fulltime: "Full-time",
  parttime: "Part-time",
  contract: "Contract",
  internship: "Internship",
};

const JOB_TYPE_ORDER = [
  "fulltime",
  "parttime",
  "contract",
  "internship",
] as const;

const WORK_MODE_LABELS: Record<string, string> = {
  onsite: "On-site",
  hybrid: "Hybrid",
  remote: "Remote",
};

const WORK_MODE_ORDER = ["onsite", "hybrid", "remote"] as const;

export const FILTER_GROUPS: readonly FilterGroup[] = [
  {
    key: "role",
    param: "role_category",
    facet: "role_category",
    title: "Role",
    labels: ROLE_LABELS,
  },
  {
    key: "level",
    param: "seniority",
    facet: "seniority",
    title: "Experience",
    labels: LEVEL_LABELS,
    order: LEVEL_ORDER,
  },
  {
    key: "mode",
    param: "work_mode",
    facet: "work_mode",
    title: "Workplace",
    labels: WORK_MODE_LABELS,
    order: WORK_MODE_ORDER,
  },
  {
    key: "type",
    param: "job_type",
    facet: "job_type",
    title: "Employment",
    labels: JOB_TYPE_LABELS,
    order: JOB_TYPE_ORDER,
  },
  {
    key: "source",
    param: "ats_type",
    facet: "ats_type",
    title: "Source",
    labels: SOURCE_LABELS,
  },
] as const;

const GROUP_BY_KEY = Object.fromEntries(
  FILTER_GROUPS.map((g) => [g.key, g]),
) as Record<FilterKey, FilterGroup>;

export const POSTED_OPTIONS: { label: string; value: number | null }[] = [
  { label: "Any time", value: null },
  { label: "Past 24 hours", value: 1 },
  { label: "Past week", value: 7 },
  { label: "Past month", value: 30 },
];

export type SortValue = "recent" | "relevance";

export const SORT_OPTIONS: {
  label: string;
  value: SortValue;
  needsQuery: boolean;
}[] = [
  { label: "Most recent", value: "recent", needsQuery: false },
  { label: "Most relevant", value: "relevance", needsQuery: true },
];

export function labelFor(key: FilterKey, value: string): string {
  return (
    GROUP_BY_KEY[key].labels[value] ??
    value.replace(/[_-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

export function postedLabel(days: number | null): string | null {
  if (days === null) return null;
  return POSTED_OPTIONS.find((o) => o.value === days)?.label ?? `Past ${days}d`;
}
