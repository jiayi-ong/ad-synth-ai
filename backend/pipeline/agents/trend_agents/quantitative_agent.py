from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types as genai_types

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import QUANTITATIVE_INSIGHTS
from tools.code_tools import execute_python

_NO_THINKING = genai_types.GenerateContentConfig(
    thinking_config=genai_types.ThinkingConfig(thinking_budget=0)
)


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[4] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def _build() -> LlmAgent:
    return LlmAgent(
        name="quantitative_analysis_agent",
        model=settings.gemini_model,
        include_contents='none',
        instruction=_load_prompt("quantitative_analysis_agent"),
        output_key=QUANTITATIVE_INSIGHTS,
        generate_content_config=_NO_THINKING,
        before_model_callback=content_safety_callback,
        tools=[FunctionTool(execute_python)],
    )


quantitative_analysis_agent = _build()


def build_quantitative_analysis_agent() -> LlmAgent:
    return _build()
