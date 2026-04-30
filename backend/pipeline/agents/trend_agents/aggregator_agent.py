from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import AGGREGATED_TREND_DATA


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[4] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


trend_aggregator_agent = LlmAgent(
    name="trend_aggregator_agent",
    model=settings.gemini_model,
    instruction=_load_prompt("trend_aggregator_agent"),
    output_key=AGGREGATED_TREND_DATA,
    before_model_callback=content_safety_callback,
)
