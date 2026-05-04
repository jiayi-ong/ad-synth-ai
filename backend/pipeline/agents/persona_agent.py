import json
import logging
from pathlib import Path
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from backend.core.config import settings
from backend.pipeline.agent_configs import TOOL_THINKING
from backend.pipeline.guardrails import content_safety_callback
from backend.pipeline.state_keys import SELECTED_PERSONA

logger = logging.getLogger(__name__)


def _load_prompt(name: str) -> str:
    return (Path(__file__).parents[3] / "prompts" / f"{name}.txt").read_text(encoding="utf-8")


async def get_campaign_personas() -> list[dict[str, Any]]:
    """
    Retrieve all available personas for the current campaign from the database.
    Returns a list of persona dicts with id, name, and traits.
    """
    from sqlalchemy import select

    from backend.db.session import AsyncSessionLocal
    from backend.models.persona import Persona

    async with AsyncSessionLocal() as db:
        rows = await db.scalars(select(Persona))
        return [
            {
                "id": p.id,
                "name": p.name,
                "traits": json.loads(p.traits) if p.traits else {},
                "generated_media_url": p.generated_media_url,
            }
            for p in rows
        ]


def _build() -> LlmAgent:
    return LlmAgent(
        name="persona_agent",
        model=settings.gemini_model,
        include_contents='none',
        instruction=_load_prompt("persona_agent"),
        output_key=SELECTED_PERSONA,
        generate_content_config=TOOL_THINKING,
        before_model_callback=content_safety_callback,
        tools=[FunctionTool(get_campaign_personas)],
    )


persona_agent = _build()
