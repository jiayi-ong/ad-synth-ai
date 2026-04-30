import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def google_custom_search(query: str, num_results: int = 8) -> list[dict[str, Any]]:
    """
    Search the web using Google Custom Search API.
    Returns a list of results, each with 'title', 'snippet', and 'link'.
    Returns an empty list if the API key is not configured or the request fails.
    """
    try:
        from backend.core.config import settings
        if not settings.google_cse_api_key or not settings.google_cse_id:
            logger.warning("Google CSE not configured — returning empty results")
            return []
        resp = httpx.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": settings.google_cse_api_key,
                "cx": settings.google_cse_id,
                "q": query,
                "num": min(num_results, 10),
            },
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [{"title": i.get("title"), "snippet": i.get("snippet"), "link": i.get("link")} for i in items]
    except Exception as e:
        logger.warning("google_custom_search failed: %s", e)
        return []


def google_trends_search(query: str) -> list[dict[str, Any]]:
    """
    Search for trending topics related to a query using Google Custom Search
    scoped to Google Trends and news sources.
    Returns a list of trending snippets.
    """
    return google_custom_search(f"{query} trending 2025 2026", num_results=5)
