from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import BRAND_CONSISTENCY


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


brand_consistency_agent = LlmAgent(
    name="brand_consistency_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("brand_consistency_agent"),
    output_key=BRAND_CONSISTENCY,
    before_model_callback=content_safety_callback,
)
