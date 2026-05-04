from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import WEB_SEARCH_RESULTS
from tools.search_tools import google_custom_search, google_trends_search
from tools.serpapi_tools import serpapi_web_search
from tools.trend_cache_tools import check_trend_cache, store_trend_cache


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def _build_tools() -> list:
    return [
        FunctionTool(check_trend_cache),
        FunctionTool(store_trend_cache),
        FunctionTool(serpapi_web_search),
        FunctionTool(google_custom_search),
        FunctionTool(google_trends_search),
    ]


web_search_agent = LlmAgent(
    name="web_search_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("web_search_agent"),
    output_key=WEB_SEARCH_RESULTS,
    before_model_callback=content_safety_callback,
    tools=_build_tools(),
)


def build_web_search_agent() -> LlmAgent:
    return LlmAgent(
        name="web_search_agent",
        model=settings.gemini_model,
        include_contents='none',
        instruction=_load_prompt("web_search_agent"),
        output_key=WEB_SEARCH_RESULTS,
        before_model_callback=content_safety_callback,
        tools=_build_tools(),
    )
