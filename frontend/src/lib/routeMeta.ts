export const SITE_URL = "https://jobdex.1mindlabs.org";

export const DEFAULT_DESCRIPTION =
  "A global index of startup hiring by city. Explore jobs on an interactive world map.";

export interface RouteMeta {
  title: string;
  description: string;
}

export const ROUTE_META: Record<string, RouteMeta> = {
  "/": {
    title: "JobDex: Map-First Job Discovery",
    description: DEFAULT_DESCRIPTION,
  },
  "/map": {
    title: "Explore the map | JobDex",
    description:
      "Browse startup jobs city by city on an interactive world map. Filter by role, seniority and remote status.",
  },
  "/how-it-works": {
    title: "How it works | JobDex",
    description:
      "How JobDex ingests, deduplicates and categorises startup job listings from public hiring APIs.",
  },
  "/legal": {
    title: "Legal | JobDex",
    description:
      "Privacy policy, terms of service and legal notices for JobDex.",
  },
  "/privacy-policy": {
    title: "Privacy Policy | JobDex",
    description:
      "What data JobDex collects, how donations are handled, and which third-party services are used.",
  },
  "/terms-of-service": {
    title: "Terms of Service | JobDex",
    description:
      "Acceptable use, listing accuracy limitations, donation policy and the MIT license for JobDex.",
  },
  "/faq": {
    title: "FAQ | JobDex",
    description:
      "Common questions about JobDex: data sources, update frequency, coverage, privacy and donations.",
  },
};

export const NOT_FOUND_META: RouteMeta = {
  title: "Page not found | JobDex",
  description: DEFAULT_DESCRIPTION,
};

export const canonicalFor = (pathname: string) =>
  pathname === "/" ? SITE_URL : `${SITE_URL}${pathname}`;
