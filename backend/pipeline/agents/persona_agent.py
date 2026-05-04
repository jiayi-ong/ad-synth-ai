import json
import logging
from pathlib import Path
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types as genai_types

from backend.core.config import settings
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import SELECTED_PERSONA

logger = logging.getLogger(__name__)

_NO_THINKING = genai_types.GenerateContentConfig(
    thinking_config=genai_types.ThinkingConfig(thinking_budget=0)
)


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


def get_campaign_personas() -> list[dict[str, Any]]:
    """
    Retrieve all available personas for the current campaign from the database.
    Returns a list of persona dicts with id, name, and traits.
    """
    import asyncio

    from sqlalchemy import select

    from backend.db.base import engine  # noqa: F401 — keeps import side-effects
    from backend.models.persona import Persona

    async def _fetch() -> list[dict]:
        from backend.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            rows = await db.scalars(select(Persona))
            result = []
            for p in rows:
                result.append({
                    "id": p.id,
                    "name": p.name,
                    "traits": json.loads(p.traits) if p.traits else {},
                    "generated_media_url": p.generated_media_url,
                })
            return result

    try:
        return asyncio.run(_fetch())
    except RuntimeError:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, _fetch())
            return future.result()


def _build() -> LlmAgent:
    return LlmAgent(
        name="persona_agent",
        model=settings.gemini_model,
        include_contents='none',
        instruction=_load_prompt("persona_agent"),
        output_key=SELECTED_PERSONA,
        generate_content_config=_NO_THINKING,
        before_model_callback=content_safety_callback,
        tools=[FunctionTool(get_campaign_personas)],
    )


persona_agent = _build()
