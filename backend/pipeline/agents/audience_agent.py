from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import AUDIENCE_ANALYSIS


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


audience_agent = LlmAgent(
    name="audience_positioning_agent",
    model=settings.gemini_model,
    instruction=_load_prompt("audience_agent"),
    output_key=AUDIENCE_ANALYSIS,
    before_model_callback=content_safety_callback,
)
