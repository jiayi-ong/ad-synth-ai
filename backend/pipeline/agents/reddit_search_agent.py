from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import REDDIT_SEARCH_RESULTS
from tools.reddit_tools import get_trending_posts, search_reddit


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


reddit_search_agent = LlmAgent(
    name="reddit_search_agent",
    model=settings.gemini_model,
    instruction=_load_prompt("reddit_search_agent"),
    output_key=REDDIT_SEARCH_RESULTS,
    before_model_callback=content_safety_callback,
    tools=[
        FunctionTool(search_reddit),
        FunctionTool(get_trending_posts),
    ],
)


def build_reddit_search_agent() -> LlmAgent:
    return LlmAgent(
        name="reddit_search_agent",
        model=settings.gemini_model,
        instruction=_load_prompt("reddit_search_agent"),
        output_key=REDDIT_SEARCH_RESULTS,
        before_model_callback=content_safety_callback,
        tools=[
            FunctionTool(search_reddit),
            FunctionTool(get_trending_posts),
        ],
    )
