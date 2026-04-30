"""
SERPAPI-based trend tools covering Instagram, TikTok, Pinterest, and general web.
A single SERPAPI_API_KEY covers all four platforms.
"""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_SERPAPI_BASE = "https://serpapi.com/search.json"


def _serpapi_request(engine: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Core SERPAPI request helper. Returns the raw results list or [] on any failure.
    The caller is responsible for extracting the relevant result key from the response.
    """
    try:
        from backend.core.config import settings
        if not settings.serpapi_api_key:
            logger.warning("SERPAPI_API_KEY not configured — returning empty results")
            return []

        resp = httpx.get(
            _SERPAPI_BASE,
            params={"engine": engine, "api_key": settings.serpapi_api_key, **params},
            timeout=25,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("SERPAPI request failed (engine=%s): %s", engine, e)
        return []


def _extract_hashtags(text: str) -> list[str]:
    """Pull #hashtag tokens from a text string."""
    import re
    return re.findall(r"#\w+", text or "")


def search_instagram_trends(
    query: str,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Search Instagram-related content via SERPAPI.

    Returns:
        List of dicts with keys: platform, title, snippet, hashtags, url.
    """
    data = _serpapi_request(
        "google",
        {"q": f"site:instagram.com {query}", "num": max_results},
    )
    items = data.get("organic_results", []) if isinstance(data, dict) else []
    results = []
    for item in items[:max_results]:
        snippet = item.get("snippet", "")
        results.append(
            {
                "platform": "Instagram",
                "title": item.get("title", ""),
                "snippet": snippet,
                "hashtags": _extract_hashtags(snippet),
                "url": item.get("link", ""),
            }
        )
    return results


def search_tiktok_trends(
    query: str,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Search TikTok-related content via SERPAPI.

    Returns:
        List of dicts with keys: platform, title, snippet, hashtags, plays, likes, url.
    """
    data = _serpapi_request(
        "google",
        {"q": f"site:tiktok.com {query}", "num": max_results},
    )
    items = data.get("organic_results", []) if isinstance(data, dict) else []
    results = []
    for item in items[:max_results]:
        snippet = item.get("snippet", "")
        results.append(
            {
                "platform": "TikTok",
                "title": item.get("title", ""),
                "snippet": snippet,
                "hashtags": _extract_hashtags(snippet),
                "plays": 0,
                "likes": 0,
                "url": item.get("link", ""),
            }
        )
    return results


def search_pinterest_trends(
    query: str,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Search Pinterest content via SERPAPI.

    Returns:
        List of dicts with keys: platform, title, snippet, board_theme, url.
    """
    data = _serpapi_request(
        "google",
        {"q": f"site:pinterest.com {query}", "num": max_results},
    )
    items = data.get("organic_results", []) if isinstance(data, dict) else []
    results = []
    for item in items[:max_results]:
        snippet = item.get("snippet", "")
        results.append(
            {
                "platform": "Pinterest",
                "title": item.get("title", ""),
                "snippet": snippet,
                "board_theme": "",
                "url": item.get("link", ""),
            }
        )
    return results


def serpapi_web_search(
    query: str,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """
    General web search via SERPAPI Google engine.
    Complements Google Custom Search with broader coverage.

    Returns:
        List of dicts with keys: title, snippet, link.
    """
    data = _serpapi_request("google", {"q": query, "num": max_results})
    items = data.get("organic_results", []) if isinstance(data, dict) else []
    return [
        {
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "link": item.get("link", ""),
        }
        for item in items[:max_results]
    ]
