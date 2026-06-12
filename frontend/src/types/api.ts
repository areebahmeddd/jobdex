export type RemoteType = "fully-remote" | "hybrid" | "onsite" | null;

export type SeniorityType =
  | "intern"
  | "junior"
  | "mid"
  | "senior"
  | "lead"
  | "staff"
  | "principal"
  | "director"
  | "vp"
  | "c-level"
  | null;

export type AtsType = "greenhouse" | "lever" | "ashby" | null;

export interface Job {
  id: string;
  company_id: string;
  company_name: string;
  company_slug: string;
  company_logo_url: string | null;
  title: string;
  description_snippet: string | null;
  city: string | null;
  country: string | null;
  country_code: string | null;
  region: string | null;
  latitude: number | null;
  longitude: number | null;
  is_remote: boolean;
  remote_type: RemoteType;
  job_type: string | null;
  seniority: SeniorityType;
  role_category: string | null;
  role_subcategory: string | null;
  tech_stack: string[];
  department: string | null;
  source_url: string;
  ats_type: AtsType;
  posted_at: string | null;
  first_seen_at: string | null;
  is_active: boolean;
  location_display: string;
}

export interface JobDetail extends Job {
  description: string | null; // HTML string
}

export interface Company {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  website: string | null;
  city: string | null;
  country: string | null;
  country_code: string | null;
  region: string | null;
  latitude: number | null;
  longitude: number | null;
  industry: string[];
  stage: string | null;
  logo_url: string | null;
  ats_type: AtsType;
  job_count: number;
  open_role_categories: string[];
  last_crawled_at: string | null;
}

export interface CityPin {
  name: string;
  slug: string;
  latitude: number;
  longitude: number;
  country_code: string;
  region: string | null;
  job_count: number;
  company_count: number;
  is_featured: boolean;
}

export interface MapCompanyPin {
  id: string;
  name: string;
  slug: string;
  city: string | null;
  country_code: string | null;
  region: string | null;
  latitude: number;
  longitude: number;
  logo_url: string | null;
  industry: string[];
  job_count: number;
}
