from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import CAMPAIGN_ARCHITECTURE


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def _build() -> LlmAgent:
    return LlmAgent(
        name="campaign_architecture_agent",
        model=settings.gemini_model,
        instruction=_load_prompt("campaign_architecture_agent"),
        output_key=CAMPAIGN_ARCHITECTURE,
        before_model_callback=content_safety_callback,
    )


campaign_architecture_agent = _build()


def build_campaign_architecture_agent() -> LlmAgent:
    """Build a fresh campaign architecture agent instance."""
    return _build()
