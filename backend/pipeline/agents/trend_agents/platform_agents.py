from pathlib import Path

from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.tools import FunctionTool

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import (
    INSTAGRAM_TREND_DATA,
    PINTEREST_TREND_DATA,
    REDDIT_TREND_DATA,
    TIKTOK_TREND_DATA,
    TWITTER_TREND_DATA,
    WEB_SEARCH_TREND_DATA,
    YOUTUBE_TREND_DATA,
)
from tools.reddit_tools import get_trending_posts, search_reddit
from tools.search_tools import google_custom_search
from tools.serpapi_tools import (
    search_instagram_trends,
    search_pinterest_trends,
    search_tiktok_trends,
    serpapi_web_search,
)
from tools.twitter_tools import search_twitter_trends
from tools.youtube_tools import search_youtube_trends


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[4] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


youtube_trend_agent = LlmAgent(
    name="youtube_trend_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("trend_youtube_agent"),
    output_key=YOUTUBE_TREND_DATA,
    before_model_callback=content_safety_callback,
    tools=[FunctionTool(search_youtube_trends)],
)

twitter_trend_agent = LlmAgent(
    name="twitter_trend_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("trend_twitter_agent"),
    output_key=TWITTER_TREND_DATA,
    before_model_callback=content_safety_callback,
    tools=[FunctionTool(search_twitter_trends)],
)

tiktok_trend_agent = LlmAgent(
    name="tiktok_trend_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("trend_tiktok_agent"),
    output_key=TIKTOK_TREND_DATA,
    before_model_callback=content_safety_callback,
    tools=[FunctionTool(search_tiktok_trends)],
)

instagram_trend_agent = LlmAgent(
    name="instagram_trend_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("trend_instagram_agent"),
    output_key=INSTAGRAM_TREND_DATA,
    before_model_callback=content_safety_callback,
    tools=[FunctionTool(search_instagram_trends)],
)

reddit_trend_agent = LlmAgent(
    name="reddit_trend_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("trend_reddit_agent"),
    output_key=REDDIT_TREND_DATA,
    before_model_callback=content_safety_callback,
    tools=[FunctionTool(search_reddit), FunctionTool(get_trending_posts)],
)

web_search_trend_agent = LlmAgent(
    name="web_search_trend_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("trend_web_agent"),
    output_key=WEB_SEARCH_TREND_DATA,
    before_model_callback=content_safety_callback,
    tools=[FunctionTool(serpapi_web_search), FunctionTool(google_custom_search)],
)

pinterest_trend_agent = LlmAgent(
    name="pinterest_trend_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("trend_pinterest_agent"),
    output_key=PINTEREST_TREND_DATA,
    before_model_callback=content_safety_callback,
    tools=[FunctionTool(search_pinterest_trends)],
)

data_collection_parallel = ParallelAgent(
    name="trend_data_collection",
    description="Parallel data collection from YouTube, Twitter/X, TikTok, Instagram, Reddit, web, and Pinterest",
    sub_agents=[
        youtube_trend_agent,
        twitter_trend_agent,
        tiktok_trend_agent,
        instagram_trend_agent,
        reddit_trend_agent,
        web_search_trend_agent,
        pinterest_trend_agent,
    ],
)
