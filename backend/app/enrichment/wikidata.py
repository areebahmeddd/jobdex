import httpx
from loguru import logger

from app.config import settings

_SEARCH_URL = "https://www.wikidata.org/w/api.php"
_SPARQL_URL = "https://query.wikidata.org/sparql"

# Description hints for disambiguating company search results.
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


def _pick_best_hit(hits: list[dict], name: str) -> str | None:
    """Return the best-matching QID from a Wikidata search result list."""
    for hit in hits:
        desc = (hit.get("description") or "").lower()
        if any(hint in desc for hint in _COMPANY_HINTS):
            logger.debug(f"[wikidata] '{name}' -> {hit['id']} via description hint ({desc[:60]})")
            return hit["id"]

    for hit in hits:
        if hit.get("label", "").lower() == name.lower():
            logger.debug(f"[wikidata] '{name}' -> {hit['id']} via exact label")
            return hit["id"]

    if hits:
        logger.debug(f"[wikidata] '{name}' -> {hits[0]['id']} (first-result fallback)")
        return hits[0]["id"]

    return None


async def _search(client: httpx.AsyncClient, query: str) -> list[dict]:
    """Call the Wikidata entity search API and return the results list."""
    params = {
        "action": "wbsearchentities",
        "search": query,
        "language": "en",
        "type": "item",
        "limit": 5,
        "format": "json",
    }
    try:
        r = await client.get(
            _SEARCH_URL,
            params=params,
            headers={"User-Agent": settings.ENRICHMENT_BOT_AGENT},
            timeout=settings.ENRICHMENT_REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("search", [])
    except Exception as exc:
        logger.warning(f"[wikidata] search failed for '{query}': {exc}")
        return []


async def search_company(client: httpx.AsyncClient, name: str) -> str | None:
    """Return the best-matching Wikidata QID for a company name."""
    hits = await _search(client, name)

    top_desc = (hits[0].get("description") or "").lower() if hits else ""
    if hits and any(hint in top_desc for hint in _COMPANY_HINTS):
        return _pick_best_hit(hits, name)

    # disambiguated fallback
    fallback_hits = await _search(client, f"{name} company")
    if fallback_hits:
        qid = _pick_best_hit(fallback_hits, name)
        if qid:
            return qid

    # return whatever pass 1 found
    return _pick_best_hit(hits, name)


async def fetch_company_data(client: httpx.AsyncClient, qid: str) -> dict:
    """Run the SPARQL query for *qid* and return a structured company dict."""
    try:
        r = await client.post(
            _SPARQL_URL,
            data={"query": _SPARQL_QUERY.format(qid=qid)},
            headers={
                "Accept": "application/json",
                "User-Agent": settings.ENRICHMENT_BOT_AGENT,
            },
            timeout=settings.ENRICHMENT_REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        bindings = r.json()["results"]["bindings"]
    except Exception as exc:
        logger.warning(f"[wikidata] SPARQL query failed for {qid}: {exc}")
        return {}

    if not bindings:
        return {}

    def _val(row: dict, key: str) -> str | None:
        """Extract a string value from a SPARQL binding row by key."""
        return row.get(key, {}).get("value")

    base: dict = {}
    founders: list[dict] = []
    industries: list[str] = []

    for row in bindings:
        if not base:
            raw_founded = _val(row, "founded")
            base = {
                "website": _val(row, "websiteUrl"),
                "twitter": _val(row, "twitterHandle"),
                "instagram": _val(row, "instagramHandle"),
                "linkedin": _val(row, "linkedinId"),
                "facebook": _val(row, "facebookId"),
                "github": _val(row, "githubOrg"),
                "logo_url": _val(row, "logoUrl"),
                "employee_count": _val(row, "employeeCount"),
                "hq": _val(row, "hqLabel"),
                "founded_year": int(raw_founded[:4]) if raw_founded else None,
            }

        industry = _val(row, "industryLabel")
        if industry and industry not in industries:
            industries.append(industry)

        founder_name = _val(row, "founderLabel")
        if founder_name and not any(f["name"] == founder_name for f in founders):
            tw = _val(row, "founderTwitter")
            li = _val(row, "founderLinkedin")
            founders.append(
                {
                    "name": founder_name,
                    "title": _val(row, "founderTitle"),
                    "twitter_url": f"https://twitter.com/{tw}" if tw else None,
                    "linkedin_url": f"https://linkedin.com/in/{li}" if li else None,
                    "photo_url": _val(row, "founderPhoto"),
                }
            )

    base["founders"] = founders
    base["industries"] = industries
    return base
