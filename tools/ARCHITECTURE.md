# Tools Architecture

The `tools/` directory contains all external API integrations exposed as `FunctionTool`s to the pipeline agents. Each tool function is pure Python — no ADK-specific code — making them independently testable.

## Design Principles

- **Graceful degradation**: Every tool checks for its API key before making network calls. If the key is absent or the API returns an error, the tool returns an empty list (not an exception). This allows the pipeline to run in local dev with zero API keys configured.
- **Normalized output**: Each platform tool returns a list of dicts with a consistent schema so the aggregator agent can process them uniformly.
- **Async-safe**: Tools used by `LlmAgent` are sync functions (ADK wraps them). Tools that need async use `httpx` with sync client or are called via `asyncio.run()`.

## Files

### `search_tools.py` — Google Custom Search

| Function | Description |
|----------|-------------|
| `google_custom_search(query, num_results)` | Queries Google Custom Search API. Returns `[{title, snippet, link}]`. Requires `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID`. |
| `google_trends_search(query)` | Alias for web trend search via CSE. |

Used by: `web_search_trend_agent`

### `reddit_tools.py` — Reddit via PRAW

| Function | Description |
|----------|-------------|
| `search_reddit(subreddit, query, limit)` | Full-text search within a subreddit. Returns `[{title, score, url, selftext}]`. Requires `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET`. |
| `get_trending_posts(subreddit, limit)` | Fetches hot posts from a subreddit. |

Used by: `reddit_trend_agent`

### `youtube_tools.py` — YouTube Data API v3

| Function | Description |
|----------|-------------|
| `search_youtube_trends(query, max_results, order)` | Searches YouTube and fetches video statistics. Returns `[{video_id, title, channel, view_count, likes, comments, published_at, url}]`. Requires `YOUTUBE_API_KEY`. |

- `order` defaults to `"relevance"`; use `"viewCount"` or `"date"` for different ranking
- Statistics (views, likes, comments) are fetched in a second API call for each result batch
- Returns empty list on quota exceeded or missing key

Used by: `youtube_trend_agent`

### `twitter_tools.py` — Twitter/X API v2 with SERPAPI fallback

| Function | Description |
|----------|-------------|
| `search_twitter_trends(query, max_results)` | Searches Twitter via Tweepy. Falls back to SERPAPI Twitter engine on `TooManyRequests`. Returns `[{text, likes, retweets, replies, created_at}]`. |
| `_serpapi_twitter_search(query, max_results)` | Internal fallback — SERPAPI Twitter search engine. |

- Free tier Twitter API: ~500 searches/month. SERPAPI fallback activates transparently on rate limit.
- Requires `TWITTER_BEARER_TOKEN`; optionally `SERPAPI_API_KEY` for fallback.

Used by: `twitter_trend_agent`

### `serpapi_tools.py` — SERPAPI Multi-Platform

Single API key covers TikTok, Instagram, Pinterest, and general web search.

| Function | Description |
|----------|-------------|
| `search_instagram_trends(query, max_results)` | SERPAPI Instagram engine. Returns `[{platform, title, snippet, hashtags, url}]`. |
| `search_tiktok_trends(query, max_results)` | SERPAPI TikTok engine. Returns `[{platform, title, snippet, hashtags, plays, likes, url}]`. |
| `search_pinterest_trends(query, max_results)` | SERPAPI Pinterest engine. Returns `[{platform, title, snippet, board_theme, url}]`. |
| `serpapi_web_search(query, max_results)` | SERPAPI general web search. Returns `[{title, snippet, link}]`. |

All functions require `SERPAPI_API_KEY`. All return empty list if key absent or API errors.

Used by: `tiktok_trend_agent`, `instagram_trend_agent`, `pinterest_trend_agent`, `web_search_trend_agent`

### `research_cache_tools.py` — Vector RAG Cache

| Function | Description |
|----------|-------------|
| `check_research_cache(query)` | Looks up similar past research using sqlite-vec cosine similarity. Returns cached result or `None`. |
| `store_research_cache(query, result)` | Stores a query-result pair with embedding in the sqlite-vec table. |

Used by: `web_search_agent`, `reddit_search_agent` (older search agents)

### `trend_cache_tools.py` — Trend Synthesis Cache

| Function | Description |
|----------|-------------|
| `check_trend_cache(query)` | Checks if synthesized trend data exists for a similar product+audience combo. Returns cached JSON or `None`. |
| `store_trend_cache(query, result)` | Persists trend synthesis output with embedding. |

Used by: `trend_synthesis_agent` (step 4 of trend sub-pipeline)

## Tool Registration

Tools are registered as `FunctionTool` objects when each agent is constructed:

```python
from google.adk.tools import FunctionTool
from tools.youtube_tools import search_youtube_trends

youtube_agent = LlmAgent(
    name="youtube_trend_agent",
    tools=[FunctionTool(search_youtube_trends)],
    ...
)
```

ADK infers the function signature and docstring to generate the tool schema presented to the LLM.

## API Key Requirements by Tool

| Tool | Required Env Var | Optional Fallback |
|------|-----------------|-------------------|
| Google Search | `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID` | — |
| Reddit | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | — |
| YouTube | `YOUTUBE_API_KEY` | — |
| Twitter | `TWITTER_BEARER_TOKEN` | `SERPAPI_API_KEY` (rate limit fallback) |
| TikTok / Instagram / Pinterest | `SERPAPI_API_KEY` | — |
| Web Search (SERPAPI) | `SERPAPI_API_KEY` | `GOOGLE_CSE_API_KEY` |
| Trend Cache | none — uses local SQLite | — |

All tools return `[]` (not an error) when their key is absent, so the pipeline runs locally with zero external API calls configured.
