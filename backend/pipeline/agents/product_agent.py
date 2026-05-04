from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import PRODUCT_PROFILE


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


product_agent = LlmAgent(
    name="product_understanding_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("product_agent"),
    output_key=PRODUCT_PROFILE,
    before_model_callback=content_safety_callback,
)
