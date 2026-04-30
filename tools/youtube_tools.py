import logging
from typing import Any

from googleapiclient.discovery import build  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def search_youtube_trends(
    query: str,
    max_results: int = 10,
    order: str = "viewCount",
) -> list[dict[str, Any]]:
    """
    Search YouTube for videos matching a query, sorted by engagement.

    Args:
        query: Search terms (e.g. "running shoes 2025 trend").
        max_results: Maximum number of videos to return (capped at 50 by the API).
        order: YouTube sort order — 'viewCount' | 'relevance' | 'rating' | 'date'.

    Returns:
        List of dicts with keys: video_id, title, channel, view_count, like_count,
        comment_count, published_at, url. Returns [] if key is absent or call fails.
    """
    try:
        from backend.core.config import settings
        if not settings.youtube_api_key:
            logger.warning("YOUTUBE_API_KEY not configured — returning empty results")
            return []

        youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)

        # Step 1: search for video IDs
        search_resp = (
            youtube.search()
            .list(
                q=query,
                part="id",
                type="video",
                order=order,
                maxResults=min(max_results, 50),
            )
            .execute()
        )
        video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
        if not video_ids:
            return []

        # Step 2: fetch statistics for those IDs
        stats_resp = (
            youtube.videos()
            .list(
                id=",".join(video_ids),
                part="snippet,statistics",
            )
            .execute()
        )

        results = []
        for item in stats_resp.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            vid_id = item["id"]
            results.append(
                {
                    "video_id": vid_id,
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                    "published_at": snippet.get("publishedAt", ""),
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                }
            )

        # Sort by view count descending so the agent sees top performers first
        results.sort(key=lambda v: v["view_count"], reverse=True)
        return results

    except Exception as e:
        logger.warning("search_youtube_trends failed for query '%s': %s", query, e)
        return []
