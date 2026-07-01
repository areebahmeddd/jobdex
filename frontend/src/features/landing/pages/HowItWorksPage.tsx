import React from "react";
import { Link } from "react-router-dom";

const STEPS: {
  number: string;
  heading: string;
  body: React.ReactNode[];
}[] = [
  {
    number: "01",
    heading: "Jobs are pulled from public hiring APIs",
    body: [
      <>
        Every supported hiring platform has its own ingester that calls the
        provider's public job board API and returns the raw listings.{" "}
        <strong>No login, no scraping, no unofficial endpoints.</strong> The
        same APIs companies use to publish their roles are what JobDex reads.
      </>,

      "Requests are retried automatically on failure with exponential backoff, and a short delay is inserted between companies during scheduled runs to be a respectful API client. Any errors are recorded against the company without stopping the rest of the crawl.",
    ],
  },
  {
    number: "02",
    heading: "Every listing is tracked and deduplicated",
    body: [
      "Each job gets a unique fingerprint based on the source platform, company slug, and the provider's own job ID. On every crawl, this fingerprint is compared against what is already in the database.",
      <>
        New listing: it gets inserted. Existing listing: only the last-seen
        timestamp is updated. Listing that disappeared from the source: it is
        marked inactive. <strong>Nothing is ever hard-deleted,</strong> so the
        full history of every role is preserved.
      </>,
    ],
  },
  {
    number: "03",
    heading: "Each job is categorized before storage",
    body: [
      "Raw data from different ATS providers arrives in inconsistent formats. Before saving, each job is normalized: the location is resolved to a canonical city name using alias lookup and fuzzy matching, remote and hybrid status is detected from the raw location string, and the job type is standardized.",
      "The role is classified into a category and subcategory, the seniority level is inferred from the title, and the tech stack is extracted from the description. This shared classification layer is what makes filtering by city, role, and seniority work consistently across all sources.",
    ],
  },
  {
    number: "04",
    heading: "Company profiles are enriched automatically",
    body: [
      "Once a company is first seen, a background enrichment job fills in its profile using three external sources. Wikidata provides structured facts like founding year, industry, funding stage, key investors, and social profile links. Wikipedia provides a long-form description when Wikidata has none.",
      <>
        Headquarters coordinates and the company logo come from Clearbit.
        Enrichment runs <strong>every 12 hours</strong> and refreshes profiles
        older than <strong>90 days</strong>.
      </>,
    ],
  },
  {
    number: "05",
    heading: "A public REST API serves all the data",
    body: [
      <>
        The backend exposes endpoints for jobs, companies, cities, search, map
        pins, and platform stats. All read endpoints are public with{" "}
        <strong>no authentication required</strong>. Job listings support
        full-text search and can be filtered by city, country, region, role,
        seniority, and remote status.
      </>,

      "Map endpoints accept a viewport bounding box and return only the pins within it, which keeps the map fast as the user pans and zooms. The full API reference is available at the Swagger docs.",
    ],
  },
  {
    number: "06",
    heading: "Everything is plotted on an interactive map",
    body: [
      "The frontend is built with React and renders the map using Leaflet on OpenStreetMap tiles. On load, city cluster pins appear showing aggregated job and company counts. As the viewport moves, company pins load for the visible area filtered by any active role or remote filter.",
      "Selecting a city shows companies hiring there. Selecting a company fetches the full profile and open roles in parallel. All filters apply in real time without a page reload.",
    ],
  },
];

const ATS_PROVIDERS: {
  name: string;
  region: string;
  slug?: string;
  color?: string;
}[] = [
  { name: "Ashby", region: "Global" },
  { name: "Greenhouse", region: "Global", slug: "greenhouse", color: "24A47F" },
  { name: "Lever", region: "Global" },
  { name: "SmartRecruiters", region: "Global" },
  { name: "Workable", region: "Global" },
  { name: "YCombinator", region: "USA", slug: "ycombinator", color: "FF6600" },
  { name: "Recruitee", region: "Europe" },
  { name: "PyjamaHR", region: "India" },
  { name: "MCF", region: "Singapore" },
];

const V = __TECH_VERSIONS__;

const STACK: {
  label: string;
  detail: string;
  version?: string;
  slug?: string;
  color?: string;
  emoji?: string;
}[] = [
  {
    label: "FastAPI",
    detail: "API framework",
    version: V.fastapi,
    slug: "fastapi",
    color: "009688",
  },
  { label: "Uvicorn", detail: "ASGI server", version: V.uvicorn, emoji: "🐍" },
  { label: "Amazon Web Services", detail: "Hosting", emoji: "☁️" },
  {
    label: "PostgreSQL",
    detail: "Neon serverless",
    version: "18.4",
    slug: "postgresql",
    color: "4169E1",
  },
  {
    label: "SQLAlchemy 2.0",
    detail: "ORM",
    version: V.sqlalchemy,
    slug: "sqlalchemy",
    color: "D71F00",
  },
  { label: "Alembic", detail: "Migrations", version: V.alembic, emoji: "🐍" },
  {
    label: "APScheduler",
    detail: "In-process scheduler",
    version: V.apscheduler,
    emoji: "🐍",
  },
  {
    label: "httpx2",
    detail: "Async HTTP client",
    version: V.httpx2,
    emoji: "🐍",
  },
  {
    label: "tenacity",
    detail: "Retry logic",
    version: V.tenacity,
    emoji: "🐍",
  },
  {
    label: "rapidfuzz",
    detail: "Fuzzy city matching",
    version: V.rapidfuzz,
    emoji: "🐍",
  },
  {
    label: "Wikidata · Wikipedia",
    detail: "Company enrichment",
    slug: "wikidata",
    color: "006699",
  },
  { label: "Clearbit", detail: "Company geo lookup" },
  {
    label: "React",
    detail: "UI framework",
    version: V.react,
    slug: "react",
    color: "61DAFB",
  },
  {
    label: "TypeScript",
    detail: "Language",
    version: V.typescript,
    slug: "typescript",
    color: "3178C6",
  },
  {
    label: "Vite",
    detail: "Build tool",
    version: V.vite,
    slug: "vite",
    color: "646CFF",
  },
  {
    label: "Leaflet",
    detail: "Map rendering",
    version: V.leaflet,
    slug: "leaflet",
    color: "199900",
  },
  {
    label: "OpenStreetMap",
    detail: "Map tiles",
    slug: "openstreetmap",
    color: "7EBC6F",
  },
  {
    label: "Tailwind CSS",
    detail: "Styling",
    version: V.tailwindcss,
    slug: "tailwindcss",
    color: "06B6D4",
  },
];

export default function HowItWorksPage() {
  return (
    <main className="min-h-screen bg-white font-sans antialiased">
      <div className="mx-auto max-w-2xl px-6 py-16">
        <Link
          to="/"
          className="text-sm text-gray-500 transition-colors hover:text-gray-700"
        >
          &larr; Back to home
        </Link>

        <div className="mt-10">
          <h1 className="text-3xl font-semibold tracking-tight text-gray-900">
            How it works
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-gray-500">
            JobDex aggregates startup job listings from public hiring APIs and
            plots them on an interactive world map. This page covers the full
            pipeline from ingestion to the map.
          </p>
        </div>

        <div className="mt-10 overflow-hidden rounded-xl border border-gray-200 bg-gray-50">
          <img
            src="/architecture.png"
            alt="JobDex system architecture diagram"
            className="w-full"
          />
          <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3">
            <span className="text-xs text-gray-500">
              System architecture overview
            </span>
            <div className="flex items-center gap-4">
              <a
                href="https://jobdex-api.1mindlabs.org/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-gray-500 underline underline-offset-2 transition-colors hover:text-gray-900"
              >
                Swagger API docs
              </a>
              <a
                href="https://github.com/areebahmeddd/jobdex/blob/main/docs/ARCHITECTURE.md"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-gray-500 underline underline-offset-2 transition-colors hover:text-gray-900"
              >
                Architecture docs
              </a>
            </div>
          </div>
        </div>

        <div className="mt-12 space-y-12">
          {STEPS.map((step) => (
            <div key={step.number} className="flex gap-6">
              <span className="mt-0.5 w-6 shrink-0 font-mono text-xs text-gray-300">
                {step.number}
              </span>
              <div className="space-y-2">
                <h2 className="text-sm font-semibold text-gray-900">
                  {step.heading}
                </h2>
                {step.body.map((para, i) => (
                  <p key={i} className="text-sm leading-relaxed text-gray-600">
                    {para}
                  </p>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-16 space-y-10 border-t border-gray-100 pt-10">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">
              Supported ATS (Applicant Tracking System) providers
            </h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {ATS_PROVIDERS.map((p) => (
                <span
                  key={p.name}
                  className="inline-flex items-center gap-1.5 rounded-md border border-gray-200 px-3 py-1 text-xs text-gray-600"
                >
                  {p.slug && (
                    <img
                      src={`https://cdn.simpleicons.org/${p.slug}/${p.color}`}
                      alt=""
                      aria-hidden="true"
                      width={12}
                      height={12}
                      className="size-3 shrink-0"
                    />
                  )}
                  {p.name}
                  <span className="text-gray-500">{p.region}</span>
                </span>
              ))}
            </div>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-gray-900">
              Technology Stack
            </h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {STACK.map((t) => (
                <span
                  key={t.label}
                  className="inline-flex items-center gap-1.5 rounded-md border border-gray-200 px-3 py-1 text-xs text-gray-600"
                >
                  {t.slug ? (
                    <img
                      src={`https://cdn.simpleicons.org/${t.slug}/${t.color}`}
                      alt=""
                      aria-hidden="true"
                      width={12}
                      height={12}
                      className="size-3 shrink-0"
                    />
                  ) : t.emoji ? (
                    <span className="shrink-0 leading-none" aria-hidden="true">
                      {t.emoji}
                    </span>
                  ) : null}
                  {t.label}
                  <span className="text-gray-500">{t.detail}</span>
                  {t.version && (
                    <span className="font-mono text-[10px] text-gray-400">
                      v{t.version}
                    </span>
                  )}
                </span>
              ))}
            </div>
          </div>

          <p className="text-xs text-gray-500">
            More providers are added regularly. For the full list including
            planned and incompatible sources, see the{" "}
            <a
              href="https://github.com/areebahmeddd/jobdex"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 transition-colors hover:text-gray-700"
            >
              GitHub repository
            </a>
            .
          </p>
        </div>
      </div>
    </main>
  );
}
