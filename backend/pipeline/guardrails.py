"""
Content safety guardrails implemented as ADK before_model_callback.
Blocks prompts containing racial slurs, violence, sexual content, or hate speech.
"""
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
