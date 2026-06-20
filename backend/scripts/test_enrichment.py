"""Test enrichment coverage across a sample of Indian and US tech companies.

Usage:
  python scripts/test_enrichment.py
"""

import asyncio

import httpx

BOT_AGENT = "JobdexEnrichmentBot/1.0 (+https://github.com/areebahmeddd/jobdex)"
REQUEST_TIMEOUT = 15.0
STEP_DELAY = 0.6

_WIKIDATA_SEARCH = "https://wikidata.org/w/api.php"
_WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
_WIKIDATA_ENTITY = "https://wikidata.org/wiki/Special:EntityData/{qid}.json"
_WIKIPEDIA_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary"
_CLEARBIT_AC = "https://autocomplete.clearbit.com/v1/companies/suggest"

_COMPANY_HINTS = frozenset(
    {
        "company",
        "startup",
        "corporation",
        "inc",
        "ltd",
        "pvt",
        "llc",
        "founded",
        "unicorn",
        "fintech",
        "platform",
        "app",
        "software",
        "enterprise",
        "saas",
        "ecommerce",
        "e-commerce",
        "neobank",
        "marketplace",
        "venture",
        "tech",
        "indian",
        "american",
        "british",
        "singapore",
        "global",
        "financial",
        "services",
        "technology",
    }
)

_SPARQL_QUERY = """
SELECT DISTINCT
  ?websiteUrl ?twitterHandle ?instagramHandle ?linkedinId ?facebookId ?githubOrg
  ?founded ?logoUrl ?employeeCount ?hqLabel ?industryLabel
  ?founderLabel ?founderTitle ?founderTwitter ?founderLinkedin ?founderPhoto
WHERE {{
  BIND(wd:{qid} AS ?company)

  OPTIONAL {{ ?company wdt:P856  ?websiteUrl. }}
  OPTIONAL {{ ?company wdt:P2002 ?twitterHandle. }}
  OPTIONAL {{ ?company wdt:P2003 ?instagramHandle. }}
  OPTIONAL {{ ?company wdt:P4264 ?linkedinId. }}
  OPTIONAL {{ ?company wdt:P2013 ?facebookId. }}
  OPTIONAL {{ ?company wdt:P6github ?githubOrg. }}
  OPTIONAL {{ ?company wdt:P571  ?founded. }}
  OPTIONAL {{ ?company wdt:P154  ?logoUrl. }}
  OPTIONAL {{ ?company wdt:P1128 ?employeeCount. }}

  OPTIONAL {{
    ?company wdt:P159 ?hq.
    ?hq rdfs:label ?hqLabel.
    FILTER(LANG(?hqLabel) = "en")
  }}
  OPTIONAL {{
    ?company wdt:P452 ?industry.
    ?industry rdfs:label ?industryLabel.
    FILTER(LANG(?industryLabel) = "en")
  }}
  OPTIONAL {{
    ?company wdt:P112 ?founder.
    ?founder rdfs:label ?founderLabel.
    FILTER(LANG(?founderLabel) = "en")
    OPTIONAL {{
      ?founder wdt:P106 ?occ.
      ?occ rdfs:label ?founderTitle.
      FILTER(LANG(?founderTitle) = "en")
    }}
    OPTIONAL {{ ?founder wdt:P2002 ?founderTwitter. }}
    OPTIONAL {{ ?founder wdt:P4264 ?founderLinkedin. }}
    OPTIONAL {{ ?founder wdt:P18  ?founderPhoto. }}
  }}
}}
LIMIT 30
"""

# (display_name, wikidata_search_term)
TEST_COMPANIES: list[tuple[str, str]] = [
    # -- US / global tech
    ("Stripe", "Stripe"),
    ("Airbnb", "Airbnb"),
    ("Notion", "Notion"),
    ("Linear", "Linear app software"),
    ("Vercel", "Vercel company"),
    ("OpenAI", "OpenAI"),
    ("Figma", "Figma"),
    ("Anthropic", "Anthropic"),
    ("Loom", "Loom video software"),
    ("Postman", "Postman API"),
    # -- Indian startups
    ("Razorpay", "Razorpay"),
    ("Groww", "Groww"),
    ("Meesho", "Meesho"),
    ("Swiggy", "Swiggy"),
    ("Zomato", "Zomato"),
    ("Paytm", "Paytm"),
    ("PhonePe", "PhonePe"),
    ("CRED", "CRED fintech India"),
    ("Zepto", "Zepto quick commerce"),
    ("FamPay", "FamPay"),
    ("Urban Company", "Urban Company India"),
    ("BrowserStack", "BrowserStack"),
    ("Zoho", "Zoho Corporation"),
]


async def _wd_search(client: httpx.AsyncClient, query: str) -> list[dict]:
    try:
        r = await client.get(
            _WIKIDATA_SEARCH,
            params={
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "type": "item",
                "limit": 5,
                "format": "json",
            },
            headers={"User-Agent": BOT_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("search", [])
    except Exception as exc:
        print(f"    [!] Wikidata search error: {exc}")
        return []


def _pick_hit(hits: list[dict]) -> str | None:
    for hit in hits:
        if any(h in (hit.get("description") or "").lower() for h in _COMPANY_HINTS):
            return hit["id"]
    return hits[0]["id"] if hits else None


async def wd_find(client: httpx.AsyncClient, search_term: str, display_name: str) -> str | None:
    hits = await _wd_search(client, search_term)
    qid = _pick_hit(hits)
    top_desc = (hits[0].get("description") or "").lower() if hits else ""
    if qid and not any(h in top_desc for h in _COMPANY_HINTS):
        fallback = await _wd_search(client, f"{display_name} company")
        fallback_qid = _pick_hit(fallback)
        if fallback_qid:
            return fallback_qid
    return qid


async def wd_fetch(client: httpx.AsyncClient, qid: str) -> dict:
    try:
        r = await client.post(
            _WIKIDATA_SPARQL,
            data={"query": _SPARQL_QUERY.format(qid=qid)},
            headers={"Accept": "application/json", "User-Agent": BOT_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        bindings = r.json()["results"]["bindings"]
    except Exception as exc:
        print(f"    [!] SPARQL error: {exc}")
        return {}

    if not bindings:
        return {}

    def v(row, k):
        return row.get(k, {}).get("value")

    base: dict = {}
    founders: list[dict] = []
    industries: list[str] = []
    for row in bindings:
        if not base:
            raw = v(row, "founded")
            base = {
                "website": v(row, "websiteUrl"),
                "twitter": v(row, "twitterHandle"),
                "instagram": v(row, "instagramHandle"),
                "linkedin": v(row, "linkedinId"),
                "facebook": v(row, "facebookId"),
                "github": v(row, "githubOrg"),
                "logo_url": v(row, "logoUrl"),
                "employee_count": v(row, "employeeCount"),
                "hq": v(row, "hqLabel"),
                "founded_year": int(raw[:4]) if raw else None,
            }
        ind = v(row, "industryLabel")
        if ind and ind not in industries:
            industries.append(ind)
        fname = v(row, "founderLabel")
        if fname and not any(f["name"] == fname for f in founders):
            tw = v(row, "founderTwitter")
            li = v(row, "founderLinkedin")
            founders.append(
                {
                    "name": fname,
                    "title": v(row, "founderTitle"),
                    "twitter_url": f"https://twitter.com/{tw}" if tw else None,
                    "linkedin_url": f"https://linkedin.com/in/{li}" if li else None,
                    "photo_url": v(row, "founderPhoto"),
                }
            )
    base["founders"] = founders
    base["industries"] = industries
    return base


async def _wiki_fetch(client: httpx.AsyncClient, title: str) -> str | None:
    """Fetch Wikipedia extract; return None for disambiguation/mainpage/404."""
    try:
        r = await client.get(
            f"{_WIKIPEDIA_SUMMARY}/{title.replace(' ', '_')}",
            headers={"User-Agent": BOT_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("type") in ("disambiguation", "mainpage"):
            return None
        return data.get("extract") or None
    except Exception:
        return None


async def _wiki_title_from_qid(client: httpx.AsyncClient, qid: str) -> str | None:
    """Get the exact English Wikipedia title for a Wikidata QID via sitelinks."""
    try:
        r = await client.get(
            _WIKIDATA_ENTITY.format(qid=qid),
            headers={"User-Agent": BOT_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        if r.status_code == 200:
            entity = r.json().get("entities", {}).get(qid, {})
            return entity.get("sitelinks", {}).get("enwiki", {}).get("title")
    except Exception:
        pass
    return None


async def wiki_summary(client: httpx.AsyncClient, name: str, qid: str | None = None) -> str | None:
    # Try resolving title from Wikidata sitelink first (most accurate)
    if qid:
        wiki_title = await _wiki_title_from_qid(client, qid)
        if wiki_title:
            result = await _wiki_fetch(client, wiki_title)
            if result:
                return result

    # Pattern-based fallback (most specific first to avoid disambiguation pages)
    for title in [f"{name} (company)", f"{name} (software)", f"{name}, Inc.", name]:
        result = await _wiki_fetch(client, title)
        if result:
            return result
    return None


async def clearbit(client: httpx.AsyncClient, name: str) -> dict:
    try:
        r = await client.get(_CLEARBIT_AC, params={"query": name}, timeout=6.0)
        if r.status_code == 200 and r.json():
            top = r.json()[0]
            domain = top.get("domain", "")
            return {
                "domain": domain,
                "logo_url": f"https://logo.clearbit.com/{domain}" if domain else None,
            }
    except Exception:
        pass
    return {}


def tick(v) -> str:
    return f"[OK] {v}" if v else "[--] not available"


def report(name: str, qid: str | None, wd: dict, about: str | None, cb: dict) -> dict:
    bar = "=" * 65
    print(f"\n{bar}")
    print(f"  {name}")
    print(bar)
    print(f"  Wikidata QID:   {qid or '(not found)'}")
    print(f"  Website:        {tick(wd.get('website'))}")
    print(f"  Twitter/X:      {tick(wd.get('twitter'))}")
    print(f"  Instagram:      {tick(wd.get('instagram'))}")
    print(f"  LinkedIn:       {tick(wd.get('linkedin'))}")
    print(f"  Facebook:       {tick(wd.get('facebook'))}")
    print(f"  GitHub:         {tick(wd.get('github'))}")
    print(f"  Founded:        {tick(wd.get('founded_year'))}")
    print(f"  HQ:             {tick(wd.get('hq'))}")
    print(f"  Industry:       {tick(', '.join(wd.get('industries', [])) or None)}")
    print(f"  Employees:      {tick(wd.get('employee_count'))}")
    founders = wd.get("founders", [])
    if founders:
        print(f"  Founders ({len(founders)}):")
        for f in founders:
            tw = f.get("twitter_url") or "n/a"
            print(f"    - {f['name']}  |  {f.get('title') or ''}  |  tw: {tw}")
    else:
        print("  Founders:       [--] not available")
    print(f"  About:          {tick(about[:180] + '...' if about and len(about) > 180 else about)}")
    print(f"  Logo (clearbit):{tick(cb.get('logo_url'))}")

    fields = {
        "logo": bool(cb.get("logo_url") or wd.get("logo_url")),
        "socials": any(wd.get(k) for k in ["twitter", "instagram", "linkedin", "facebook"]),
        "founded": bool(wd.get("founded_year")),
        "founders": bool(founders),
        "about": bool(about),
        "hq": bool(wd.get("hq")),
        "industry": bool(wd.get("industries")),
    }
    covered = sum(fields.values())
    print(f"  Coverage:       {covered}/7  [{', '.join(k for k, v in fields.items() if v)}]")
    return fields


async def main():
    print("=" * 65)
    print("  JOBDEX ENRICHMENT TEST")
    print("  Wikidata + Wikipedia (sitelink) + Clearbit Autocomplete")
    print(f"  {len(TEST_COMPANIES)} companies")
    print("=" * 65)

    totals: dict[str, int] = {
        k: 0 for k in ["logo", "socials", "founded", "founders", "about", "hq", "industry"]
    }
    failures: dict[str, list[str]] = {k: [] for k in totals}

    async with httpx.AsyncClient(
        headers={"User-Agent": BOT_AGENT}, follow_redirects=True
    ) as client:
        for display_name, search_term in TEST_COMPANIES:
            print(f"\n  Fetching: {display_name}...")

            qid = await wd_find(client, search_term, display_name)
            wd_data = await wd_fetch(client, qid) if qid else {}
            about = await wiki_summary(client, display_name, qid)
            cb_data = await clearbit(client, display_name)

            fields = report(display_name, qid, wd_data, about, cb_data)
            for k, ok in fields.items():
                if ok:
                    totals[k] += 1
                else:
                    failures[k].append(display_name)

            await asyncio.sleep(STEP_DELAY)

    total = len(TEST_COMPANIES)
    print(f"\n\n{'=' * 65}")
    print(f"  COVERAGE SUMMARY  ({total} companies)")
    print(f"{'=' * 65}")
    for field, count in totals.items():
        pct = int(count / total * 100)
        bar = "#" * (count * 2) + "-" * ((total - count) * 2)
        print(f"  {field:<12}  [{bar}]  {count}/{total}  ({pct}%)")
        if failures[field]:
            print(f"               missing: {', '.join(failures[field])}")
    print("\n  NOTE: funding / investors / valuation / benefits n/a no free source.")
    print("        Store as nullable, display 'Not available' in the UI.")
    print(f"{'=' * 65}\n")


if __name__ == "__main__":
    asyncio.run(main())
