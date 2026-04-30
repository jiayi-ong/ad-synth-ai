import logging
from typing import Any

logger = logging.getLogger(__name__)


def search_reddit(subreddit: str, query: str, limit: int = 15) -> list[dict[str, Any]]:
    """
    Search a subreddit for posts matching a query.
    Returns a list of posts with 'title', 'score', 'url', and 'selftext' (truncated).
    Returns an empty list if Reddit credentials are not configured or the request fails.
    """
    try:
        from backend.core.config import settings
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            logger.warning("Reddit credentials not configured — returning empty results")
            return []
        import praw
        reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )
        results = []
        for post in reddit.subreddit(subreddit).search(query, limit=limit, sort="relevance", time_filter="year"):
            results.append({
                "title": post.title,
                "score": post.score,
                "url": post.url,
                "selftext": post.selftext[:400] if post.selftext else "",
            })
        return results
    except Exception as e:
        logger.warning("search_reddit failed: %s", e)
        return []


def get_trending_posts(subreddit: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Get currently trending posts from a subreddit (hot posts).
    Returns a list of posts with 'title', 'score', and 'url'.
    """
    try:
        from backend.core.config import settings
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            return []
        import praw
        reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )
        return [
            {"title": p.title, "score": p.score, "url": p.url}
            for p in reddit.subreddit(subreddit).hot(limit=limit)
        ]
    except Exception as e:
        logger.warning("get_trending_posts failed: %s", e)
        return []
