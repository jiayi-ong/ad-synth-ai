from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types as genai_types

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import MARKET_SEGMENTATION
from tools.code_tools import execute_python
from tools.knowledge_store_tools import check_knowledge_store

_NO_THINKING = genai_types.GenerateContentConfig(
    thinking_config=genai_types.ThinkingConfig(thinking_budget=0)
)


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def _build() -> LlmAgent:
    return LlmAgent(
        name="market_segmentation_agent",
        model=settings.gemini_model,
        instruction=_load_prompt("market_segmentation_agent"),
        output_key=MARKET_SEGMENTATION,
        generate_content_config=_NO_THINKING,
        before_model_callback=content_safety_callback,
        tools=[
            FunctionTool(execute_python),
            FunctionTool(check_knowledge_store),
        ],
    )


market_segmentation_agent = _build()


def build_market_segmentation_agent() -> LlmAgent:
    """Build a fresh market segmentation agent instance for use inside a LoopAgent."""
    return _build()
