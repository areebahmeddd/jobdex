export type CityPin = {
  name: string;
  slug: string;
  latitude: number;
  longitude: number;
  country_code: string | null;
  region: string | null;
  job_count: number;
  company_count: number;
};

export type CompanyPin = {
  id: string;
  name: string;
  slug: string;
  city: string | null;
  country_code: string | null;
  region: string | null;
  latitude: number;
  longitude: number;
  logo_url: string | null;
  job_count: number;
  industry: string[];
};

export type CompanyListItem = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  website: string | null;
  city: string | null;
  country_code: string | null;
  region: string | null;
  latitude: number | null;
  longitude: number | null;
  industry: string[];
  stage: string | null;
  founded_year: number | null;
  logo_url: string | null;
  job_count: number;
  open_role_categories: string[];
};

export type CompanyDetail = CompanyListItem & {
  wikidata_id: string | null;
  founders: Record<string, unknown>[] | null;
  key_investors: Record<string, unknown>[] | null;
  total_funding_usd: number | null;
  funding_stage: string | null;
  business_model: string | null;
  headcount_range: string | null;
  benefits: Record<string, unknown>[] | null;
  office_address: string | null;
  social_links: Record<string, string> | null;
  work_modes: string[];
  departments: string[];
};

export type CompanyOffice = {
  city: string;
  country_code: string | null;
  latitude: number;
  longitude: number;
  job_count: number;
};

export type Job = {
  id: string;
  company_id: string;
  company_name: string;
  company_slug: string;
  company_logo_url: string | null;
  title: string;
  description_snippet: string | null;
  city: string | null;
  country_code: string | null;
  region: string | null;
  is_remote: boolean;
  remote_type: string | null;
  seniority: string | null;
  job_type: string | null;
  role_category: string | null;
  role_subcategory: string | null;
  department: string | null;
  tech_stack: string[];
  source_url: string;
  posted_at: string | null;
  location_display: string;
};

export type JobDetail = Job & {
  location_raw: string | null;
  description: string | null;
};

export type PanelView =
  | "default"
  | "companies"
  | "company-detail"
  | "jobs"
  | "job-detail";
