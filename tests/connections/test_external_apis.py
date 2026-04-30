"""Connection tests for all external trend research APIs.

Each test is auto-skipped if the relevant key is not set.
Each test makes exactly one minimal live API call.
"""
import os

import pytest

pytestmark = pytest.mark.connection


# ── Google Custom Search ──────────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("GOOGLE_CSE_API_KEY") or not os.environ.get("GOOGLE_CSE_ID"),
    reason="GOOGLE_CSE_API_KEY or GOOGLE_CSE_ID not set",
)
def test_google_cse_returns_results():
    import httpx
    api_key = os.environ["GOOGLE_CSE_API_KEY"]
    cx = os.environ["GOOGLE_CSE_ID"]
    url = "https://www.googleapis.com/customsearch/v1"
    r = httpx.get(url, params={"key": api_key, "cx": cx, "q": "running shoes ads", "num": 1}, timeout=15)
    assert r.status_code == 200, f"CSE returned {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "items" in data or "searchInformation" in data
    print(f"\n  Google CSE: {data.get('searchInformation', {}).get('totalResults', '?')} total results")
    print("  Status: GOOGLE CSE CONNECTED ✓")


# ── SERPAPI ───────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("SERPAPI_API_KEY"),
    reason="SERPAPI_API_KEY not set",
)
def test_serpapi_returns_results():
    import httpx
    api_key = os.environ["SERPAPI_API_KEY"]
    r = httpx.get(
        "https://serpapi.com/search",
        params={"api_key": api_key, "engine": "google", "q": "running shoes trending ads", "num": 1},
        timeout=20,
    )
    assert r.status_code == 200, f"SERPAPI returned {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "organic_results" in data or "search_information" in data
    print(f"\n  SERPAPI: {len(data.get('organic_results', []))} results")
    print("  Status: SERPAPI CONNECTED ✓")


# ── YouTube Data API v3 ───────────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("YOUTUBE_API_KEY"),
    reason="YOUTUBE_API_KEY not set",
)
def test_youtube_returns_videos():
    import httpx
    api_key = os.environ["YOUTUBE_API_KEY"]
    r = httpx.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "key": api_key,
            "part": "snippet",
            "q": "running shoe advertisement",
            "maxResults": 1,
            "type": "video",
        },
        timeout=15,
    )
    assert r.status_code == 200, f"YouTube API returned {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "items" in data
    print(f"\n  YouTube: found {len(data['items'])} video(s)")
    print("  Status: YOUTUBE API CONNECTED ✓")


# ── Reddit PRAW ───────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("REDDIT_CLIENT_ID") or not os.environ.get("REDDIT_CLIENT_SECRET"),
    reason="REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not set",
)
def test_reddit_reads_subreddit():
    import praw
    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ.get("REDDIT_USER_AGENT", "ad-synth-ai/0.1"),
    )
    posts = list(reddit.subreddit("marketing").hot(limit=1))
    assert len(posts) > 0, "No Reddit posts returned — check credentials"
    print(f"\n  Reddit: '{posts[0].title[:60]}...'")
    print("  Status: REDDIT CONNECTED ✓")


# ── Twitter / X API v2 ────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("TWITTER_BEARER_TOKEN"),
    reason="TWITTER_BEARER_TOKEN not set",
)
def test_twitter_search_returns_tweets():
    import httpx
    token = os.environ["TWITTER_BEARER_TOKEN"]
    r = httpx.get(
        "https://api.twitter.com/2/tweets/search/recent",
        params={"query": "running shoes -is:retweet lang:en", "max_results": 10},
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    assert r.status_code == 200, f"Twitter API returned {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "data" in data or "meta" in data
    count = len(data.get("data", []))
    print(f"\n  Twitter: {count} tweet(s) returned")
    print("  Status: TWITTER API CONNECTED ✓")
