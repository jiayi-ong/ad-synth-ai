from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import TREND_RESEARCH


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[4] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


trend_critic_agent = LlmAgent(
    name="trend_critic_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("trend_critic_agent"),
    output_key=TREND_RESEARCH,
    before_model_callback=content_safety_callback,
)
