from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import SENTIMENT_INSIGHTS


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[4] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def _build() -> LlmAgent:
    return LlmAgent(
        name="sentiment_analysis_agent",
        model=settings.gemini_model,
        instruction=_load_prompt("sentiment_analysis_agent"),
        output_key=SENTIMENT_INSIGHTS,
        before_model_callback=content_safety_callback,
    )


sentiment_analysis_agent = _build()


def build_sentiment_analysis_agent() -> LlmAgent:
    return _build()
