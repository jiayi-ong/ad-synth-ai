from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import TREND_RESEARCH


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


trend_synthesis_agent = LlmAgent(
    name="trend_synthesis_agent",
    model=settings.gemini_model,
    instruction=_load_prompt("trend_synthesis_agent"),
    output_key=TREND_RESEARCH,
    before_model_callback=content_safety_callback,
)


def build_trend_synthesis_agent() -> LlmAgent:
    return LlmAgent(
        name="trend_synthesis_agent",
        model=settings.gemini_model,
        instruction=_load_prompt("trend_synthesis_agent"),
        output_key=TREND_RESEARCH,
        before_model_callback=content_safety_callback,
    )
