import httpx2 as httpx
from loguru import logger

from app.config import settings

_WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary"
_WIKIDATA_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"


async def _fetch(client: httpx.AsyncClient, title: str) -> str | None:
    """Return the plain-text extract for a Wikipedia page title, or None on failure."""
    url = f"{_WIKI_SUMMARY}/{title.replace(' ', '_')}"
    try:
        r = await client.get(
            url,
            headers={"User-Agent": settings.ENRICHMENT_BOT_AGENT},
            timeout=settings.ENRICHMENT_REQUEST_TIMEOUT,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("type") in ("disambiguation", "mainpage"):
            return None
        return data.get("extract") or None
    except Exception as exc:
        logger.warning(f"[wikipedia] fetch failed for '{title}': {exc}")
    return None


async def title_from_wikidata(client: httpx.AsyncClient, qid: str) -> str | None:
    """Resolve the English Wikipedia title for a Wikidata entity via sitelinks."""
    url = _WIKIDATA_ENTITY.format(qid=qid)
    try:
        r = await client.get(
            url,
            headers={"User-Agent": settings.ENRICHMENT_BOT_AGENT},
            timeout=settings.ENRICHMENT_REQUEST_TIMEOUT,
        )
        if r.status_code != 200:
            return None
        entities = r.json().get("entities", {})
        entity = entities.get(qid, {})
        enwiki = entity.get("sitelinks", {}).get("enwiki", {})
        return enwiki.get("title") or None
    except Exception as exc:
        logger.warning(f"[wikipedia] wikidata sitelink lookup failed for {qid}: {exc}")
    return None


async def find_summary(
    client: httpx.AsyncClient,
    company_name: str,
    wikidata_qid: str | None = None,
) -> str | None:
    """Return the Wikipedia plain-text summary for a company."""
    if wikidata_qid:
        wiki_title = await title_from_wikidata(client, wikidata_qid)
        if wiki_title:
            result = await _fetch(client, wiki_title)
            if result:
                return result

    candidates = [
        f"{company_name} (company)",
        f"{company_name} (software)",
        f"{company_name} (app)",
        f"{company_name}, Inc.",
        company_name,
    ]
    for title in candidates:
        result = await _fetch(client, title)
        if result:
            return result
    return None
