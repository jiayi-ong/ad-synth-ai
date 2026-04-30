from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import MARKETING_OUTPUT


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


marketing_agent = LlmAgent(
    name="marketing_recommendation_agent",
    model=settings.gemini_model,
    instruction=_load_prompt("marketing_agent"),
    output_key=MARKETING_OUTPUT,
    before_model_callback=content_safety_callback,
)
