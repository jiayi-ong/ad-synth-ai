from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import CREATIVE_DIRECTIONS


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


creative_agent = LlmAgent(
    name="creative_strategy_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("creative_agent"),
    output_key=CREATIVE_DIRECTIONS,
    before_model_callback=content_safety_callback,
)
