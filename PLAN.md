# JobDex — Engineering Plan

## Project Vision

JobDex is a **map-first, open-source startup job board** — a global alternative to [nextdoor.company](https://nextdoor.company). Instead of search boxes and infinite scroll, users discover jobs geographically on an interactive globe/map. The data is entirely sourced by directly calling company-specific ATS (Applicant Tracking System) career APIs — no scraping HTML, no middle-man aggregators.

The long-term target is **50+ ATS integrations** spanning every major hiring region and industry — engineering, product, design, marketing, finance, legal, medical/healthcare, culinary/hospitality, education, and more.

---

## Current System Architecture

### Backend Stack

| Layer       | Technology                             |
|-------------|----------------------------------------|
| API         | FastAPI + Uvicorn                      |
| ORM         | SQLAlchemy 2.0 (Mapped[] style)        |
| Database    | Neon serverless PostgreSQL             |
| Migrations  | Alembic                                |
| HTTP Client | httpx2 (async, with tenacity retries)  |
| Scheduler   | APScheduler (in-process, no worker)    |
| Enrichment  | Wikidata + Wikipedia + Clearbit        |
| Packaging   | uv                                     |

### Ingestion Pipeline

Each ATS is implemented as a `BaseIngester` subclass with three required methods:

- `fetch_raw(slug)` — call the ATS public API, return raw list of job dicts
- `extract_job_id(raw)` — extract a stable, ATS-side job ID
- `build_job(raw, company, slug)` — normalise raw dict into a `Job` ORM object

`BaseIngester` handles dedup (SHA-256 hash of `ats_type:slug:job_id`), soft-deactivation, retry logic, geo lookup via Clearbit, and backfill of company HQ from job locations.

The normalisation pipeline (`app/ingestion/normalizer/`) converts raw location strings, role titles, seniority signals, and tech stack mentions into canonical structured fields using fuzzy matching (rapidfuzz), pattern files, and optional Nominatim geocoding.

### Background Jobs

| Job ID               | Interval | Description                                |
|----------------------|----------|--------------------------------------------|
| `ingest_all`         | 6 h      | Crawl all active companies, oldest-first   |
| `enrich_pending`     | 12 h     | Enrich companies with null `enriched_at`   |
| `discover_companies` | 24 h     | Seed new companies from bulk discovery     |

### Discovery

Ingesters can optionally implement `discover()` to bulk-seed companies from the ATS platform itself (e.g. YCombinator's company list). YCombinator is currently the only ingester with `discover()` implemented.

---

## Existing ATS Integrations

| # | ATS          | Region  | API Endpoint                                             | Auth | Discovery |
|---|--------------|---------|----------------------------------------------------------|------|-----------|
| 1 | Ashby        | Global  | `api.ashbyhq.com/posting-api/job-board/{slug}`           | None | No        |
| 2 | Greenhouse   | Global  | `boards-api.greenhouse.io/v1/boards/{slug}/jobs`         | None | No        |
| 3 | Lever        | Global  | `api.lever.co/v0/postings/{slug}?mode=json`              | None | No        |
| 4 | YCombinator  | US      | `api.ycombinator.com/v0.1/companies?q={slug}`            | None | Yes       |

All four have **completely public, no-auth JSON APIs** — the gold standard for JobDex integrations.

---

## Proposed New ATS Integrations

Organised by region, with verified endpoint patterns and implementation notes. Priority tiers indicate implementation order.

---

### Americas

#### 1. SmartRecruiters
>
> **Priority: P0 — Implement first**

- **Region:** Global (very strong in Americas + Europe)
- **Usage:** Enterprise — Twitter/X, McDonald's, Visa, LinkedIn, Zalando, 4,000+ companies
- **API:** `GET https://api.smartrecruiters.com/v1/companies/{slug}/postings`
- **Auth:** None (public posting API, no key required)
- **Response:** JSON — `{ "content": [{ "id", "name", "location", "department", "typeOfEmployment", "experienceLevel" }] }`
- **Job ID:** `posting.id` (UUID)
- **Pagination:** `?limit=100&offset=0`
- **Discovery:** None (no bulk company list), but `discover()` can seed from known Fortune 500 slugs
- **Notes:** SmartRecruiters has a distinct "Posting API" separate from their main Customer API. The Posting API is fully public for reading published jobs. Company slugs follow their internal `companyIdentifier` (e.g. `McDonalds`, `Zalando`, `VisaInc`).
- **Industries:** Engineering, Marketing, Operations, Finance, Legal, Medical — cross-domain

#### 2. Workable
>
> **Priority: P0 — Implement first**

- **Region:** Global (US, UK, EU, Middle East, India — 30,000+ companies)
- **Usage:** SMB & mid-market — used in tech, retail, hospitality, healthcare, legal
- **API:** `POST https://apply.workable.com/{slug}/api/v3/jobs`
- **Auth:** None (public subdomain API)
- **Request body:** `{"query": "", "location": [], "department": [], "worktype": [], "remote": []}`
- **Response:** JSON — `{ "results": [{ "id", "title", "city", "country_code", "remote", "department", "type" }] }`
- **Job ID:** `job.shortcode` (e.g. `"ABC123"`)
- **Detail:** `GET https://apply.workable.com/{slug}/api/v3/jobs/{shortcode}`
- **Notes:** Uses `POST` for the listing (unlike others). The `slug` is the company's Workable subdomain. Many non-tech industries use Workable — doctors' clinics, law firms, restaurants, logistics.
- **Industries:** Engineering, Marketing, Hospitality, Medical/Healthcare, Legal — very broad

#### 3. JazzHR
>
> **Priority: P1**

- **Region:** Americas (US + Canada primary)
- **Usage:** Staffing agencies, US SMBs, 15,000+ companies
- **API:** `GET https://{slug}.jazz.co/api/jobs`
- **Auth:** None (public JSON endpoint)
- **Response:** JSON array of job objects with `id`, `title`, `city`, `state`, `country`, `department`
- **Job ID:** `job.id`
- **Notes:** JazzHR domains follow `{company}.jazz.co`. Widely used in hospitality, retail, and staffing. The `discover()` method could enumerate from a seeded list. Strong in North America.
- **Industries:** Engineering, Marketing, Hospitality, Retail, Staffing

#### 4. Breezy HR
>
> **Priority: P1**

- **Region:** Americas (US + Canada primary, some EU)
- **Usage:** SMBs across many verticals, 17,000+ companies
- **API:** `GET https://{slug}.breezy.hr/positions.json` or `https://api.breezy.hr/v3/company/{company_id}/positions`
- **Auth:** None for public positions endpoint via subdomain
- **Response:** JSON with position list, location, department, type
- **Job ID:** `position._id`
- **Notes:** Each company gets a `{slug}.breezy.hr` subdomain. A secondary approach is the public positions JSON at the subdomain route. Many agencies and healthcare providers use Breezy.
- **Industries:** Engineering, Healthcare, Staffing, Education, Marketing

---

### Europe

#### 5. Recruitee
>
> **Priority: P0 — Implement first**

- **Region:** Europe (Netherlands-based, very strong in NL/DE/UK/PL/CZ)
- **Usage:** European tech startups and scaleups, 8,000+ companies
- **API:** `GET https://{slug}.recruitee.com/api/offers`
- **Auth:** None (fully public JSON)
- **Response:** JSON — `{ "offers": [{ "id", "title", "city", "country", "department", "remote", "employment_type_code" }] }`
- **Job ID:** `offer.id`
- **Notes:** Per-company subdomain API, clean JSON response, works without any auth. Extremely popular with European tech companies. The slug is the company's Recruitee subdomain. Very strong in Amsterdam, Berlin, Warsaw, Prague, Lisbon tech scenes.
- **Industries:** Engineering, Product, Marketing, Data — predominantly tech

#### 6. Teamtailor
>
> **Priority: P1**

- **Region:** Europe (Sweden-based, dominant in Scandinavia, expanding UK/EU)
- **Usage:** 9,000+ companies globally, very strong in Sweden/Norway/Denmark/Finland
- **API:** `GET https://api.teamtailor.com/v1/jobs?filter[status]=published`
- **Auth:** Token API key (required per company)
- **Headers:** `Authorization: Token token={api_key}`, `X-Api-Version: 20240404`
- **Response:** JSON:API format with job attributes and included relationships
- **Job ID:** `job.id` (numeric)
- **Notes:** Teamtailor requires each company to issue a public-scoped read API key. However, many companies expose their key openly via embedded career site widgets. The integration strategy should seed companies that have made their API keys available, or contact companies for integration partnership. Very popular in Scandinavia and increasingly the UK. Strong across engineering, sales, and marketing roles.
- **Implementation Note:** Unlike the zero-auth ATS, this requires per-company API keys stored in a `company.ats_api_key` field. Adds a new credential model.
- **Industries:** Engineering, Sales, Marketing, Product

#### 7. Personio
>
> **Priority: P1**

- **Region:** Europe (Germany-based, dominant in DACH — Germany/Austria/Switzerland; also used in UK, Spain, Netherlands)
- **Usage:** 14,000+ European companies, strongest in German-speaking markets
- **API (XML feed):** `GET https://{company-subdomain}.jobs.personio.de/xml`
- **API (JSON jobs):** `GET https://api.personio.de/v1/recruiting/positions` (requires bearer token)
- **Auth:** XML feed is public; JSON API requires OAuth token
- **Recommended approach:** Parse public XML career feed
- **Response (XML):** Job listings with title, department, location, schedule (full/part-time)
- **Job ID:** `position.id`
- **Notes:** Personio is the dominant HR platform in German-speaking Europe. Their public XML career feed at `{subdomain}.jobs.personio.de/xml` requires no auth and returns structured job data. The career site slug is the company's Personio subdomain. Massively important for DACH-region coverage. Used by companies across all industries — engineering, medical (hospitals), law firms, retail, manufacturing.
- **Industries:** Engineering, Marketing, Medical/Healthcare, Legal, Finance, Manufacturing — very broad DACH coverage

#### 8. Welcome to the Jungle (WTTJ)
>
> **Priority: P2**

- **Region:** Europe (France-based, dominant in France, growing in Europe/US)
- **Usage:** 5,000+ companies, premium brand employer platform
- **API:** `GET https://api.welcometothejungle.com/api/v1/organizations/{slug}/jobs`
- **Auth:** API key required (partnership-based)
- **Alternative:** Public GraphQL at `https://api.welcometothejungle.com/graphql`
- **Notes:** Welcome to the Jungle is the dominant job platform in France — it is to French tech/startups what LinkedIn Jobs is elsewhere. Their public company pages expose structured job data. The GraphQL API may be accessible without auth for published jobs. Key for French, Belgian, and international companies hiring in Paris/Lyon/Bordeaux. Strong in engineering, creative, and marketing roles.
- **Industries:** Engineering, Creative/Design, Marketing, Product — French market focus

---

### Middle East

#### 9. Bayt
>
> **Priority: P2**

- **Region:** Middle East & North Africa (MENA) — dominant platform
- **Usage:** 40M+ registered users, largest job platform in the Arab world
- **Headquarters:** Dubai, UAE
- **API:** No official public API; structured HTML scraping via career pages
- **Approach:** Scrape `https://www.bayt.com/en/company/{slug}/jobs/`
- **Notes:** Bayt is the LinkedIn of the Arab world. It covers all GCC countries (UAE, Saudi Arabia, Qatar, Kuwait, Bahrain, Oman) and extends to Egypt, Jordan, Lebanon, Morocco. Most companies in the region post here. HTML scraping of public job listings is feasible with BeautifulSoup. Used for all industries including engineering, oil & gas, finance, healthcare, hospitality, construction.
- **Implementation Note:** Requires HTML scraping instead of JSON API. The `BaseIngester.fetch_raw` method would use `httpx` + HTML parsing. A custom `ats_type = "bayt"` ingester.
- **Industries:** Engineering, Finance, Oil & Gas, Healthcare, Hospitality, Construction, Banking

#### 10. GulfTalent
>
> **Priority: P3**

- **Region:** GCC (Gulf Cooperation Council) — UAE, Saudi Arabia, Qatar, Kuwait
- **Usage:** Major platform for GCC professional hiring; strong in finance, engineering, marketing
- **API:** No official public API; HTML scraping approach
- **Approach:** Scrape `https://www.gulftalent.com/jobs` with company/industry filters
- **Notes:** GulfTalent focuses on professional and management-level roles in the Gulf. Especially strong for oil & gas, banking, hospitality (hotel chains), and management consulting. Complements Bayt for the premium segment.
- **Industries:** Finance, Oil & Gas, Management Consulting, Engineering, Hospitality

#### 11. Naukrigulf
>
> **Priority: P2**

- **Region:** India + GCC (bridges India and the Gulf)
- **Usage:** Large expat Indian community working in Gulf countries; 1M+ jobs
- **API:** No official public API; structured HTML scraping
- **Approach:** Scrape `https://www.naukrigulf.com/jobs-in-{country}`
- **Notes:** Naukrigulf is operated by Naukri.com (Info Edge India). It's the primary platform for Indians seeking jobs in Gulf countries and for Gulf companies recruiting from India. Strong for IT, engineering, healthcare, and accounting.
- **Industries:** IT/Engineering, Healthcare (nurses, doctors), Accounting, Construction, Retail

---

### India

#### 12. Freshteam (Freshworks)
>
> **Priority: P1**

- **Region:** India (Freshworks is a Chennai-based company), also SE Asia, US, UK
- **Usage:** 9,000+ companies; extremely popular among Indian startups and mid-size companies
- **API:** `GET https://{company}.freshteam.com/api/open_positions` *(requires API key)*
- **Auth:** Bearer token (API key from Freshteam dashboard)
- **Response:** JSON array of job objects
- **Job ID:** `position.id`
- **Notes:** Freshteam is Freshworks' ATS product. Very widely adopted in the Indian startup ecosystem — Swiggy, Dunzo, Meesho, Cure.fit, and thousands of mid-market Indian companies use it. It requires an API key, but like Teamtailor, this can be fetched from companies willing to integrate. The Freshteam API follows standard Bearer token auth.
- **Implementation Note:** Requires per-company API key in `company.ats_api_key`. Shares the same credential model as Teamtailor.
- **Industries:** Engineering, Product, Marketing, Operations — Indian startup ecosystem

#### 13. iimjobs / Instahyre
>
> **Priority: P3**

- **Region:** India (pan-India, strong in Bengaluru/Mumbai/Delhi NCR)
- **Usage:** 500,000+ premium Indian professionals, 3,000+ companies
- **API:** No official public API; HTML scraping
- **Approach:** Scrape `https://www.instahyre.com/jobs/` or `https://www.iimjobs.com/j/`
- **Notes:** iimjobs focuses on MBA/management professionals; Instahyre (its sister platform) targets software engineers. Both are operated by iimjobs.com. Critical for covering India's mid-to-senior professional segment. Widely used by Indian product companies, consulting firms, banks.
- **Industries:** Management Consulting, Finance, Technology, Marketing — India professional

---

## ATS Integration Tiers

### Tier 1 — Zero Auth Public JSON APIs (Implement immediately)

These match the architecture of existing integrations:

| ATS            | Endpoint Pattern                                    | Region      |
|----------------|-----------------------------------------------------|-------------|
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/{slug}/postings` | Global   |
| Workable       | `apply.workable.com/{slug}/api/v3/jobs` (POST)      | Global      |
| Recruitee      | `{slug}.recruitee.com/api/offers`                   | Europe      |
| JazzHR         | `{slug}.jazz.co/api/jobs`                           | Americas    |
| Breezy HR      | `{slug}.breezy.hr/positions.json`                   | Americas    |

### Tier 2 — Public XML Feed or Token-Based (Implement with credential model)

| ATS         | Approach                                             | Region  |
|-------------|------------------------------------------------------|---------|
| Personio    | XML feed at `{slug}.jobs.personio.de/xml`            | Europe  |
| Teamtailor  | JSON API with per-company read token                 | Europe  |
| Freshteam   | JSON API with per-company Bearer token               | India   |
| Welcome to the Jungle | GraphQL or partnership API                 | Europe  |

### Tier 3 — HTML Scraping (Implement with scraper module)

| ATS/Platform | Approach                                            | Region      |
|--------------|-----------------------------------------------------|-------------|
| Bayt         | HTML scrape of company job pages                    | Middle East |
| Naukrigulf   | HTML scrape of job listings                         | India/Gulf  |
| GulfTalent   | HTML scrape of company listings                     | Middle East |
| iimjobs      | HTML scrape                                         | India       |

---

## Note on WeWork

**WeWork is not an ATS.** WeWork is a coworking space / flexible office company. It is not a hiring platform, job board, or applicant tracking system used by other companies for recruitment. WeWork posts its own internal jobs through third-party ATS platforms (historically Greenhouse and Lever), both of which are already integrated in JobDex.

If you are thinking of a startup job discovery platform, you may be thinking of **Wellfound** (formerly AngelList Talent) — already listed in the roadmap below.

---

## Long-term 50 ATS Roadmap

Beyond the 13 new proposals above, the path to 50 ATS integrations includes:

### Globally Used Enterprise ATS

| ATS                   | Notes                                                                  |
|-----------------------|------------------------------------------------------------------------|
| Workday               | Unofficial career site API; `{company}.wd{n}.myworkdayjobs.com/en-US/{board}/jobs/data` — no auth, returns JSON. Used by Microsoft, Apple, Amazon, most Fortune 500. |
| iCIMS                 | Enterprise US ATS, public career portals; scraping approach            |
| Taleo (Oracle)        | Very large enterprise; career site scraping at `{company}.taleo.net`  |
| SAP SuccessFactors    | Widely used in MENA, India, EU enterprise; career site scraping        |
| Jobvite               | US mid-market; `jobs.jobvite.com/api` public JSON                      |
| Bullhorn              | Staffing/recruitment agencies globally; staffing-specific ATS          |

### Americas — Additional Platforms

| ATS/Platform      | Notes                                                               |
|-------------------|---------------------------------------------------------------------|
| Wellfound (AngelList Talent) | Global startup jobs platform, strong in US — formerly AngelList Talent; `wellfound.com/company/{slug}/jobs`; used by thousands of startups |
| Rippling          | Growing US HR/payroll/ATS company; has a public jobs board at `rippling.com/company/{slug}/jobs` |
| Paycor            | US mid-market HR; public career sites with structured job listings  |
| Homebase          | US hourly workers platform — restaurants, retail, healthcare; niche  |
| UKG (Kronos/UltiPro) | Enterprise US HR; career portals at `recruiting.ultipro.com/{slug}` |

### Europe — Additional Platforms

| ATS/Platform      | Notes                                                                |
|-------------------|----------------------------------------------------------------------|
| Softgarden        | German ATS, popular in manufacturing/automotive (`{slug}.softgarden.io`) |
| Pinpoint          | UK-based ATS, SMBs (`jobs.pinpointhq.com`)                          |
| Traffit           | Polish ATS, popular in CEE (Central/Eastern Europe)                 |
| Sympa             | Finnish HR system, popular in Nordics                               |
| Greenhouse (EU companies) | Already integrated, but European company coverage can grow  |
| Talentech         | Norwegian ATS group (Webcruiter, Talmundo) — Scandinavian coverage  |
| Rexx Systems      | German ATS used in manufacturing/automotive (`{slug}.rexx-systems.com`) |
| JOIN              | German-based, free ATS popular with EU SMBs — `join.com/api`        |

### Middle East — Additional Platforms

| ATS/Platform  | Notes                                                                   |
|---------------|-------------------------------------------------------------------------|
| Wuzzuf        | Egypt's leading job platform; structured career pages for scraping      |
| Drjobspro     | Pan-Arab professional jobs, UAE focus                                   |
| Mihnati       | Saudi Arabia-specific job platform                                      |
| Akhtaboot     | Jordan/Levant region job platform                                       |
| LinkedIn MENA | Majority of regional companies use LinkedIn for job postings (complex auth) |

### India — Additional Platforms

| ATS/Platform    | Notes                                                                  |
|-----------------|------------------------------------------------------------------------|
| Darwinbox       | Indian HCM used by large enterprises (HCL, Piramal, Myntra)            |
| Keka HR         | Indian HR platform, popular SMBs — growing fast                        |
| Zoho Recruit    | Indian (Zoho) ATS — REST API available                                  |
| Naukri.com      | India's dominant job board (Info Edge); no public API but HTML-scrapable |
| Hirect          | Indian app for direct hiring in tech startups (mobile-first)           |
| Hirist          | Tech-specific Indian job portal                                        |

### Latin America

| ATS/Platform    | Notes                                                                      |
|-----------------|----------------------------------------------------------------------------|
| Computrabajo    | Operates in 21 countries across Spain + LATAM (Mexico, Colombia, Argentina, Chile, Peru, Venezuela, Ecuador, Panama, Costa Rica, etc.) — largest Spanish-language job board network; structured HTML scraping |
| OCC Mundial     | Mexico's leading job platform since 1998, 1M+ registered professionals; HTML scraping at `occ.com.mx` |
| Catho           | Brazil's major job board, owned by Springer Nature; strong in São Paulo/Rio de Janeiro |
| Infojobs (Spain/LATAM) | Very popular in Spain and growing in Latin America; structured career pages |
| Bumeran         | Argentina-focused, also covers Chile, Peru, Panama; HTML scraping        |
| Vagas.com.br    | Brazil-specific, strong in São Paulo tech market                         |

### Asia Pacific — Australia / New Zealand

| ATS/Platform  | Notes                                                                   |
|---------------|-------------------------------------------------------------------------|
| SEEK (Australia/NZ) | Largest job site in ANZ — `work.seek.com.au/api/chalice-search/v4/search`; also operates in SE Asia |
| LinkedIn AU/NZ | Majority of professional Australian companies hire via LinkedIn (complex auth) |

### Asia Pacific — Southeast Asia

| ATS/Platform  | Notes                                                                   |
|---------------|-------------------------------------------------------------------------|
| JobStreet     | Dominant in Malaysia, Philippines, Singapore, Indonesia — owned by SEEK Group; `jobstreet.com` and `jobstreet.com.sg` |
| JobsDB        | Popular in Hong Kong, Thailand, Indonesia — also owned by SEEK Group    |
| MyCareersFuture | Singapore government-backed jobs portal operated by Workforce Singapore; structured API |
| Tech in Asia  | Tech-specific job board for SE Asian startups                           |

### Asia Pacific — East Asia

| ATS/Platform  | Notes                                                                   |
|---------------|-------------------------------------------------------------------------|
| JobKorea      | South Korea's largest job portal (잡코리아) — `jobkorea.co.kr`; strong in Seoul tech/finance |
| Saramin       | South Korea's second largest job platform (사람인) — also has an API     |
| 104.com.tw    | Taiwan's leading job board since 1999; structured data at `104.com.tw` |
| CakeResume    | Taiwan-based, expanding across East/Southeast Asia — startup/tech focus |
| Indeed Japan  | Major Japanese market; `jp.indeed.com`                                  |
| Recruit Holdings (Japan) | Japan's largest HR company — operates Indeed, HotWorks, and regional ATS; Tokyo-dominant |

### Russia / CIS

> ⚠️ Note: Including hh.ru is a decision for project maintainers to make based on geopolitical considerations.

| ATS/Platform  | Notes                                                                   |
|---------------|-------------------------------------------------------------------------|
| HeadHunter (hh.ru) | Dominant job platform in Russia, Kazakhstan, Belarus, Ukraine (pre-2022), Armenia, Georgia, Azerbaijan. Has a documented public API at `github.com/hhru/api`. Vacancy search (`GET https://api.hh.ru/vacancies?employer_id={id}`) works with free app-level OAuth registration. 60M+ CVs, 1M+ active companies. Covers all industries including IT, engineering, medical, finance. |
| SuperJob      | Russia's second largest job board; structured career pages; `superjob.ru` |

### Turkey

| ATS/Platform  | Notes                                                                   |
|---------------|-------------------------------------------------------------------------|
| Kariyer.net   | Turkey's largest job board since 1999; dominant in Istanbul/Ankara tech market; covers engineering, finance, marketing, healthcare; `kariyer.net` — HTML scraping approach |
| LinkedIn Turkey | Many Turkish companies post exclusively on LinkedIn (complex auth)    |

### Sub-Saharan Africa

| ATS/Platform  | Notes                                                                   |
|---------------|-------------------------------------------------------------------------|
| Jobberman     | Nigeria and West Africa's largest job board (founded 2009); covers Lagos/Abuja tech ecosystem; `jobberman.com` — HTML scraping; strong in IT, marketing, finance, telecom |
| Careers24     | South Africa's leading job board; strong in Johannesburg/Cape Town; `careers24.com` — HTML scraping; finance, engineering, retail, healthcare |
| PNet          | South Africa's second largest job platform; `pnet.co.za` — HTML scraping; professional and specialist roles |
| Fuzu          | East Africa-focused (Kenya, Uganda, Nigeria); funded, growing platform; `fuzu.com` |
| Shortlist     | Employer-side hiring platform in Kenya/India; structured API possible  |
| MyJobMag      | West Africa (Nigeria, Ghana, Kenya); IT/marketing/finance focus        |

### Industry-Specific ATS (Across Regions)

| ATS/Platform        | Industry           | Notes                                              |
|---------------------|--------------------|----------------------------------------------------|
| NHS Jobs (UK)       | Healthcare         | National Health Service jobs — UK public sector    |
| AMN Healthcare      | Healthcare (US)    | Largest healthcare staffing in US                  |
| Hirequest           | Hospitality/Temp   | Hospitality and temp staffing platform             |
| Culinary Agents     | Culinary           | Restaurant and culinary industry jobs              |
| Poached Jobs        | Culinary           | Restaurant/food service hiring platform            |
| Law Crossing        | Legal              | Legal jobs across US law firms                     |
| Lawjobs.com         | Legal              | UK legal sector jobs                               |
| Mediabistro         | Media/Creative     | Media, journalism, content roles                   |
| Dice                | Engineering/Tech   | US technology and engineering specialist jobs      |

---

## Engineering Decisions & Implementation Guidelines

### Adding a New Tier 1 ATS (Zero Auth)

1. Create `backend/app/ingestion/{ats_name}.py`
2. Subclass `BaseIngester` with `ats_type = "{ats_name}"`
3. Implement `fetch_raw(slug)`, `extract_job_id(raw)`, `build_job(raw, company, slug)`
4. Register in `app/ingestion/__init__.py`
5. Add to `ats_type` enum in models if needed
6. Write integration test in `tests/integration/`
7. Add to `README.md` data sources table

### Adding a Tier 2 ATS (Per-company credential)

1. Add `ats_api_key` field to `Company` model (nullable)
2. Pass key through `BaseIngester.ingest(company, db)` to `fetch_raw`
3. Store encrypted/hashed key in company record at registration time

### Adding a Tier 3 ATS (HTML Scraping)

1. Use `httpx` + `BeautifulSoup4` (add to `pyproject.toml`)
2. Implement `fetch_raw` to return normalised list of dicts from HTML
3. Be mindful of rate limits and user-agent headers
4. Implement `extract_job_id` using unique URL slugs or page-internal IDs

### Discovery at Scale

For ATS platforms that have public company directories (like YCombinator), implement `discover()` to enumerate companies automatically. For platforms without directories, maintain a curated `data/companies_{ats_type}.json` seed file.

### Normalisation Coverage

As new ATS are added from non-English speaking regions (DACH, France, MENA, India), the following normalisation modules need updates:

- `data/cities.json` — add tier-2 and tier-3 cities for covered regions
- `data/role_patterns.json` — add role patterns in German, French, Arabic transliterations
- `app/ingestion/normalizer/location.py` — improve alias coverage for Middle Eastern and Indian city variants (e.g. "Bengaluru" vs "Bangalore", "Gurugram" vs "Gurgaon", "Riyadh" vs "Ar Riyad")

---

## Implementation Priority Summary

| Priority | ATS               | Region          | Type          | Estimated Effort |
|----------|-------------------|-----------------|---------------|-----------------|
| P0       | SmartRecruiters   | Global          | Public JSON   | 1 day            |
| P0       | Workable          | Global          | Public JSON   | 1 day            |
| P0       | Recruitee         | Europe          | Public JSON   | 0.5 day          |
| P1       | JazzHR            | Americas        | Public JSON   | 0.5 day          |
| P1       | Breezy HR         | Americas        | Public JSON   | 0.5 day          |
| P1       | Personio          | Europe          | Public XML    | 1 day            |
| P1       | Teamtailor        | Europe          | Token API     | 1.5 days         |
| P1       | Freshteam         | India           | Token API     | 1.5 days         |
| P1       | Workday           | Global/Enterprise| JSON scrape  | 2 days           |
| P2       | Welcome to Jungle | Europe          | API/GraphQL   | 2 days           |
| P2       | Bayt              | Middle East     | HTML scrape   | 2 days           |
| P2       | Naukrigulf        | India/Gulf      | HTML scrape   | 1.5 days         |
| P3       | GulfTalent        | Middle East     | HTML scrape   | 1.5 days         |
| P3       | iimjobs/Instahyre | India           | HTML scrape   | 1.5 days         |
| Future   | 35+ others        | All regions     | Various       | Ongoing          |

**Total after P0-P1 complete:** 12 ATS integrations (current 4 + 8 new)
**Total after all priorities:** 17 ATS integrations
**Long-term target:** 50 ATS integrations across all regions and industries
