export type CityPin = {
  name: string;
  slug: string;
  latitude: number;
  longitude: number;
  country_code: string;
  region: string;
  job_count: number;
  company_count: number;
  is_featured: boolean;
};

export type CompanyPin = {
  id: string;
  name: string;
  slug: string;
  city: string;
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
  logo_url: string | null;
  job_count: number;
  open_role_categories: string[];
};

export type CompanyDetail = CompanyListItem & {
  founded_year: number | null;
};

export type CompanyOffice = {
  city: string;
  country_code: string;
  latitude: number;
  longitude: number;
  job_count: number;
};

export type Job = {
  id: string;
  company_name: string;
  company_slug: string;
  company_logo_url: string | null;
  title: string;
  description_snippet: string | null;
  city: string | null;
  country_code: string | null;
  is_remote: boolean;
  remote_type: string | null;
  seniority: string | null;
  role_category: string | null;
  tech_stack: string[];
  source_url: string;
  posted_at: string | null;
  location_display: string;
};

export type JobDetail = Job & { description: string | null };

export type PanelView =
  | "default"
  | "companies"
  | "company-detail"
  | "jobs"
  | "job-detail";
