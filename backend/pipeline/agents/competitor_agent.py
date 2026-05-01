from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import COMPETITOR_ANALYSIS
from tools.research_cache_tools import check_research_cache, store_research_cache
from tools.search_tools import google_custom_search


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


competitor_agent = LlmAgent(
    name="competitor_agent",
    model=settings.gemini_model,
    instruction=_load_prompt("competitor_agent"),
    output_key=COMPETITOR_ANALYSIS,
    before_model_callback=content_safety_callback,
    tools=[
        FunctionTool(check_research_cache),
        FunctionTool(store_research_cache),
        FunctionTool(google_custom_search),
    ],
)


def build_competitor_agent() -> LlmAgent:
    """Build a fresh (unparented) competitor agent for standalone use."""
    return LlmAgent(
        name="competitor_agent",
        model=settings.gemini_model,
        instruction=_load_prompt("competitor_agent"),
        output_key=COMPETITOR_ANALYSIS,
        before_model_callback=content_safety_callback,
        tools=[
            FunctionTool(check_research_cache),
            FunctionTool(store_research_cache),
            FunctionTool(google_custom_search),
        ],
    )
