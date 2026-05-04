from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, exit_loop

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import LOOP_EVAL_SIGNAL


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def _build() -> LlmAgent:
    return LlmAgent(
        name="loop_evaluator_agent",
        model=settings.gemini_model,
        include_contents='none',
        instruction=_load_prompt("loop_evaluator_agent"),
        output_key=LOOP_EVAL_SIGNAL,
        before_model_callback=content_safety_callback,
        tools=[FunctionTool(exit_loop)],
    )


loop_evaluator_agent = _build()


def build_loop_evaluator_agent() -> LlmAgent:
    """Build a fresh loop evaluator agent instance."""
    return _build()
