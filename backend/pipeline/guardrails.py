"""
Content safety guardrails and JSON validation callbacks for ADK agents.
"""
import json
import logging
import re

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

logger = logging.getLogger(__name__)

_BLOCKLIST = re.compile(
    r"\b(murder|rape|pornograph|racist|slur|hate speech|terrorist|suicide|self.harm)\b",
    re.IGNORECASE,
)

# Only scan user-supplied inputs, not accumulated agent outputs.
# Scanning llm_request.contents causes cascade false positives: once an upstream
# agent writes marketing copy containing a blocklisted word ("killer pricing",
# "Naked Nutrition"), every downstream agent's assembled prompt triggers the block.
_USER_INPUT_KEYS = (
    "raw_product_description",
    "raw_marketing_brief",
    "extra_input",
    "brand_profile_context",
)


def content_safety_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """
    Inspect user-supplied inputs before any LLM call.
    Returns a structured error response if blocked content is detected, else None.
    """
    state = callback_context.state or {}
    text_to_scan = ""
    for key in _USER_INPUT_KEYS:
        val = state.get(key) or ""
        if isinstance(val, dict):
            val = json.dumps(val)
        text_to_scan += val + " "

    if _BLOCKLIST.search(text_to_scan):
        logger.warning("Content safety block triggered for agent: %s", callback_context.agent_name)
        blocked_response = types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text='{"error": "Content safety guardrail triggered — prompt contains blocked content."}')],
                    ),
                    finish_reason=types.FinishReason.SAFETY,
                )
            ]
        )
        return LlmResponse(content=blocked_response.candidates[0].content)
    return None


def json_validation_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """
    After-model callback: if the agent output is not valid JSON, inject a
    correction message so ADK re-prompts the model for valid JSON.
    Returns None (pass-through) if output is already valid JSON.
    """
    try:
        content = llm_response.content
        if not content or not content.parts:
            return None
        text = content.parts[0].text or ""
        # Strip common markdown fences before checking
        stripped = text.strip()
        if stripped.startswith("```"):
            # Split on fence: ['', 'json\n{...}\n', ''] — take middle piece [1]
            stripped = stripped.split("```", 2)[1] if "```" in stripped[3:] else stripped[3:]
            stripped = stripped.lstrip("json").strip()
        json.loads(stripped)
        return None  # Valid JSON — pass through unchanged
    except (json.JSONDecodeError, AttributeError, IndexError):
        logger.warning("JSON validation failed for agent %s — requesting correction", callback_context.agent_name)
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text=(
                    "Your previous response was not valid JSON. "
                    "Return ONLY a valid JSON object with no markdown fences, "
                    "no surrounding text, and no explanation."
                ))],
            )
        )
