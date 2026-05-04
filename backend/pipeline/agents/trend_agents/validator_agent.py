from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import TREND_RESEARCH


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[4] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def _build() -> LlmAgent:
    return LlmAgent(
        name="trend_validator_agent",
        model=settings.gemini_model,
        include_contents='none',
        instruction=_load_prompt("trend_validator_agent"),
        output_key=TREND_RESEARCH,
        before_model_callback=content_safety_callback,
    )


trend_validator_agent = _build()


def build_trend_validator_agent() -> LlmAgent:
    return _build()
