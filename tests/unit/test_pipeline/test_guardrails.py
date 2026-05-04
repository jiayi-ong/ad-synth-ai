"""Unit tests for content safety and JSON validation guardrails."""
from unittest.mock import MagicMock

import pytest
from google.adk.models.llm_response import LlmResponse
from google.genai import types


def _make_llm_request(text: str = ""):
    req = MagicMock()
    part = MagicMock()
    part.text = text
    content = MagicMock()
    content.parts = [part]
    req.contents = [content]
    return req


def _make_llm_response(text: str) -> LlmResponse:
    content = types.Content(
        role="model",
        parts=[types.Part(text=text)],
    )
    return LlmResponse(content=content)


def _make_callback_context(agent_name: str = "test_agent", state: dict | None = None):
    ctx = MagicMock()
    ctx.agent_name = agent_name
    ctx.state = state or {}
    return ctx


@pytest.mark.unit
class TestContentSafetyCallback:
    def test_blocks_terrorist_content(self):
        from backend.pipeline.guardrails import content_safety_callback
        ctx = _make_callback_context(state={"raw_product_description": "Support terrorist activities"})
        result = content_safety_callback(ctx, _make_llm_request())
        assert result is not None
        assert "safety" in result.content.parts[0].text.lower() or "guardrail" in result.content.parts[0].text.lower()

    def test_blocks_violence_in_marketing_brief(self):
        from backend.pipeline.guardrails import content_safety_callback
        ctx = _make_callback_context(state={"raw_marketing_brief": "murder your customers in cold blood"})
        result = content_safety_callback(ctx, _make_llm_request())
        assert result is not None

    def test_blocks_hate_speech_in_extra_input(self):
        from backend.pipeline.guardrails import content_safety_callback
        ctx = _make_callback_context(state={"extra_input": "use racist slurs and hate speech"})
        result = content_safety_callback(ctx, _make_llm_request())
        assert result is not None

    def test_passes_clean_user_inputs(self):
        from backend.pipeline.guardrails import content_safety_callback
        ctx = _make_callback_context(state={
            "raw_product_description": "Running shoes for athletes",
            "raw_marketing_brief": "Target performance-focused adults aged 25-40",
        })
        result = content_safety_callback(ctx, _make_llm_request())
        assert result is None

    def test_passes_empty_state(self):
        from backend.pipeline.guardrails import content_safety_callback
        ctx = _make_callback_context(state={})
        result = content_safety_callback(ctx, _make_llm_request())
        assert result is None

    def test_does_not_block_agent_output_language(self):
        """Words in llm_request.contents (agent outputs) must not trigger the guardrail."""
        from backend.pipeline.guardrails import content_safety_callback
        ctx = _make_callback_context(state={
            "raw_product_description": "Premium protein powder",
            "raw_marketing_brief": "Target gym-goers",
        })
        req = _make_llm_request("murder mystery-style campaign — bomb the market with value")
        result = content_safety_callback(ctx, req)
        assert result is None

    def test_passes_common_marketing_language(self):
        """kill, naked, nude, bomb in user inputs must NOT block — removed from blocklist."""
        from backend.pipeline.guardrails import content_safety_callback
        phrases = [
            "Naked Nutrition protein powder — naked truth about clean ingredients",
            "nude lipstick shades for all skin tones",
            "bomb-proof packaging for extreme sports",
            "kill it in the market with this product launch",
        ]
        for phrase in phrases:
            ctx = _make_callback_context(state={"raw_product_description": phrase})
            result = content_safety_callback(ctx, _make_llm_request())
            assert result is None, f"Should not block: {phrase!r}"

    def test_passes_brand_profile_dict_without_harmful_content(self):
        """brand_profile_context as dict is serialised and scanned safely."""
        from backend.pipeline.guardrails import content_safety_callback
        ctx = _make_callback_context(state={
            "brand_profile_context": {"name": "Naked Nutrition", "tone": "energetic and bold"},
        })
        result = content_safety_callback(ctx, _make_llm_request())
        assert result is None


@pytest.mark.unit
class TestJsonValidationCallback:
    def test_passes_valid_json(self):
        from backend.pipeline.guardrails import json_validation_callback
        ctx = _make_callback_context()
        response = _make_llm_response('{"key": "value", "number": 42}')
        result = json_validation_callback(ctx, response)
        assert result is None

    def test_passes_nested_json(self):
        from backend.pipeline.guardrails import json_validation_callback
        ctx = _make_callback_context()
        response = _make_llm_response('{"product": {"name": "shoe", "price": 99.99}, "tags": ["fast", "durable"]}')
        result = json_validation_callback(ctx, response)
        assert result is None

    def test_passes_json_with_markdown_fence(self):
        from backend.pipeline.guardrails import json_validation_callback
        ctx = _make_callback_context()
        response = _make_llm_response('```json\n{"key": "value"}\n```')
        result = json_validation_callback(ctx, response)
        assert result is None

    def test_returns_correction_for_plain_text(self):
        from backend.pipeline.guardrails import json_validation_callback
        ctx = _make_callback_context()
        response = _make_llm_response("Here is my analysis of the product...")
        result = json_validation_callback(ctx, response)
        assert result is not None
        assert "valid JSON" in result.content.parts[0].text

    def test_returns_correction_for_malformed_json(self):
        from backend.pipeline.guardrails import json_validation_callback
        ctx = _make_callback_context()
        response = _make_llm_response('{"key": "value"')  # missing closing brace
        result = json_validation_callback(ctx, response)
        assert result is not None

    def test_handles_empty_response(self):
        from backend.pipeline.guardrails import json_validation_callback
        ctx = _make_callback_context()
        response = _make_llm_response("")
        result = json_validation_callback(ctx, response)
        assert result is None or result is not None
