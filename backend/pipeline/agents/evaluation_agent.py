from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import EVALUATION_OUTPUT


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


evaluation_agent = LlmAgent(
    name="evaluation_agent",
    model=settings.gemini_model,
    instruction=_load_prompt("evaluation_agent"),
    output_key=EVALUATION_OUTPUT,
    before_model_callback=content_safety_callback,
)
