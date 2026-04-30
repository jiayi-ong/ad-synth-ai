import logging
from typing import Any

import tweepy  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def _serpapi_twitter_search(query: str, max_results: int) -> list[dict[str, Any]]:
    """SERPAPI fallback for Twitter/X results when the direct API is unavailable."""
    try:
        from backend.core.config import settings
        if not settings.serpapi_api_key:
            return []
        import httpx
        resp = httpx.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "twitter",
                "q": query,
                "num": max_results,
                "api_key": settings.serpapi_api_key,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        tweets = data.get("tweets_results", data.get("organic_results", []))
        results = []
        for t in tweets[:max_results]:
            results.append(
                {
                    "text": t.get("snippet", t.get("description", "")),
                    "like_count": t.get("likes", 0),
                    "retweet_count": t.get("retweets", 0),
                    "reply_count": t.get("replies", 0),
                    "created_at": t.get("date", ""),
                    "source": "serpapi",
                }
            )
        return results
    except Exception as e:
        logger.warning("_serpapi_twitter_search failed: %s", e)
        return []


def search_twitter_trends(
    query: str,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Search X/Twitter for recent tweets matching a query.

    Uses the Twitter API v2 Bearer Token as the primary path. Falls back to SERPAPI
    if the bearer token is absent or rate-limited (HTTP 429). Returns [] if both fail.

    Returns:
        List of dicts with keys: text, like_count, retweet_count, reply_count,
        created_at. Returns [] if neither path is configured or both fail.
    """
    try:
        from backend.core.config import settings
        if not settings.twitter_bearer_token:
            logger.warning("TWITTER_BEARER_TOKEN not configured — falling back to SERPAPI")
            return _serpapi_twitter_search(query, max_results)

        client = tweepy.Client(bearer_token=settings.twitter_bearer_token, wait_on_rate_limit=False)
        response = client.search_recent_tweets(
            query=f"{query} -is:retweet lang:en",
            max_results=min(max_results, 100),
            tweet_fields=["public_metrics", "created_at"],
        )
        if not response.data:
            return []

        results = []
        for tweet in response.data:
            metrics = tweet.public_metrics or {}
            results.append(
                {
                    "text": tweet.text,
                    "like_count": metrics.get("like_count", 0),
                    "retweet_count": metrics.get("retweet_count", 0),
                    "reply_count": metrics.get("reply_count", 0),
                    "created_at": str(tweet.created_at) if tweet.created_at else "",
                    "source": "twitter_api",
                }
            )

        results.sort(key=lambda t: t["like_count"], reverse=True)
        return results

    except Exception as e:
        # Tweepy raises tweepy.errors.TooManyRequests on 429
        if "429" in str(e) or "TooManyRequests" in type(e).__name__:
            logger.warning("Twitter API rate limited — falling back to SERPAPI: %s", e)
            return _serpapi_twitter_search(query, max_results)
        logger.warning("search_twitter_trends failed for query '%s': %s", query, e)
        return []
