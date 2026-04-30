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
    r"\b(kill|murder|rape|pornograph|nude|naked|racist|slur|hate speech|"
    r"bomb|terrorist|suicide|self.harm)\b",
    re.IGNORECASE,
)


def content_safety_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """
    Inspect the assembled prompt before it reaches the LLM.
    If blocked content is detected, return a structured error response instead.
    """
    prompt_text = ""
    for content in llm_request.contents or []:
        for part in content.parts or []:
            if hasattr(part, "text") and part.text:
                prompt_text += part.text + " "

    if _BLOCKLIST.search(prompt_text):
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
            stripped = stripped.split("```", 2)[-1] if "```" in stripped[3:] else stripped[3:]
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
