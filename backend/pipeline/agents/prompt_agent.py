from pathlib import Path

from google.adk.agents import LlmAgent

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import IMAGE_GEN_PROMPT


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


prompt_agent = LlmAgent(
    name="prompt_engineering_agent",
    model=settings.gemini_model,
        include_contents='none',
    instruction=_load_prompt("prompt_agent"),
    output_key=IMAGE_GEN_PROMPT,
    before_model_callback=content_safety_callback,
)
