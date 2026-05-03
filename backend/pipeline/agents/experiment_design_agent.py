from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import EXPERIMENT_DESIGN
from tools.code_tools import execute_python


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def _build() -> LlmAgent:
    return LlmAgent(
        name="experiment_design_agent",
        model=settings.gemini_model,
        instruction=_load_prompt("experiment_design_agent"),
        output_key=EXPERIMENT_DESIGN,
        before_model_callback=content_safety_callback,
        tools=[FunctionTool(execute_python)],
    )


experiment_design_agent = _build()


def build_experiment_design_agent() -> LlmAgent:
    """Build a fresh experiment design agent instance."""
    return _build()
