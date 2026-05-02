from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import TREND_RESEARCH
from tools.trend_cache_tools import check_trend_cache, store_trend_cache


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[4] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


trend_synthesis_agent = LlmAgent(
    name="trend_synthesis_agent",
    model=settings.gemini_model,
    instruction=_load_prompt("trend_synthesis_agent"),
    output_key=TREND_RESEARCH,
    before_model_callback=content_safety_callback,
    tools=[FunctionTool(check_trend_cache), FunctionTool(store_trend_cache)],
)
