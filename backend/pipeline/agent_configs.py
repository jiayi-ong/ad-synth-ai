"""
Shared GenerateContentConfig constants for pipeline agents.

NO_THINKING   — thinking_budget=0. Use for agents WITHOUT tools. Prevents any thinking
                overhead and eliminates MALFORMED_FUNCTION_CALL risk (no function calls
                means no risk). Safe on all Gemini model versions; ThinkingConfig is
                silently ignored by models that don't support thinking (e.g. 2.0-flash).

TOOL_THINKING — thinking_budget=settings.agent_thinking_budget (default 1024). Use for
                agents WITH tools. A non-zero budget is required on gemini-2.5-flash:
                setting budget=0 on a thinking model causes empty text output after tool
                calls (output_key never written). On gemini-2.0-flash the config is
                ignored, so this constant is safe across all model versions.
                The default of 1024 is small enough to keep cost/latency low while
                preventing MALFORMED_FUNCTION_CALL at high context sizes (~44k+ tokens).
                Tune via AGENT_THINKING_BUDGET env var without code changes.
"""
from google.genai import types as genai_types

from backend.core.config import settings

NO_THINKING = genai_types.GenerateContentConfig(
    thinking_config=genai_types.ThinkingConfig(thinking_budget=0)
)

TOOL_THINKING = genai_types.GenerateContentConfig(
    thinking_config=genai_types.ThinkingConfig(
        thinking_budget=settings.agent_thinking_budget
    )
)
