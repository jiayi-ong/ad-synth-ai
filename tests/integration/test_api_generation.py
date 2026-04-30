"""
Integration tests for the generation endpoint.
Uses mock image provider (IMAGE_GEN_PROVIDER=mock) and mocked ADK Runner.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.pipeline.state_keys import (
    AUDIENCE_ANALYSIS,
    CREATIVE_DIRECTIONS,
    IMAGE_GEN_PROMPT,
    MARKETING_OUTPUT,
    PRODUCT_PROFILE,
    SELECTED_PERSONA,
    TREND_RESEARCH,
)


def _make_mock_runner(pipeline_state: dict):
    """Creates a mock ADK runner that yields agent completion events."""

    class MockEvent:
        def __init__(self, author, state):
            self.author = author
            self._state = state

        def is_final_response(self):
            return True

    class MockSession:
        def __init__(self, state):
            self.state = state

    async def mock_run_async(*args, **kwargs):
        agent_map = {
            "product_understanding_agent": PRODUCT_PROFILE,
            "audience_positioning_agent": AUDIENCE_ANALYSIS,
            "trend_research_agent": TREND_RESEARCH,
            "creative_strategy_agent": CREATIVE_DIRECTIONS,
            "persona_agent": SELECTED_PERSONA,
            "prompt_engineering_agent": IMAGE_GEN_PROMPT,
            "marketing_recommendation_agent": MARKETING_OUTPUT,
        }
        for agent_name, state_key in agent_map.items():
            yield MockEvent(author=agent_name, state=pipeline_state)

    mock = MagicMock()
    mock.run_async = mock_run_async

    session_state = {**pipeline_state}
    mock_session = MockSession(session_state)
    mock.session_service = AsyncMock()
    mock.session_service.create_session = AsyncMock(return_value=mock_session)
    mock.session_service.get_session = AsyncMock(return_value=mock_session)
    return mock


SAMPLE_PIPELINE_STATE = {
    PRODUCT_PROFILE: {"product_type": "running shoe", "overall_summary": "Test shoe"},
    AUDIENCE_ANALYSIS: {"primary_audience": {"description": "Athletes"}, "mismatch_flags": []},
    TREND_RESEARCH: {"trends": [], "overall_summary": "No trends cached"},
    CREATIVE_DIRECTIONS: {"recommended_headline": "Run Fast", "creative_directions": []},
    SELECTED_PERSONA: {"persona": {"name": "Alex"}, "source": "new"},
    IMAGE_GEN_PROMPT: {
        "image_gen_prompt": "[General Description]\nA premium ad.\n\n[Quality]\nHigh resolution.",
        "ab_variant_prompt": "[General Description]\nA variant ad.",
        "ab_change_description": "Changed scene",
    },
    MARKETING_OUTPUT: {"product_slogan": "Run Lighter", "recommended_platforms": []},
}


def test_generation_endpoint_returns_sse_stream(client, auth_headers, campaign, product):
    mock_runner = _make_mock_runner(SAMPLE_PIPELINE_STATE)
    with patch("backend.pipeline.runner_module.get_runner", return_value=mock_runner):
        r = client.post(
            "/generate",
            json={
                "campaign_id": campaign["id"],
                "product_id": product["id"],
                "persona_ids": [],
                "target_audience": "Athletes aged 25-35",
            },
            headers=auth_headers,
        )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]

    # Parse SSE events
    events = []
    for line in r.text.split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    event_types = [e["event"] for e in events]
    assert "started" in event_types
    assert "done" in event_types
    # Should have agent_complete events or image_ready
    assert any(e in event_types for e in ["agent_complete", "image_ready", "image_generating"])


def test_generation_requires_auth(client, campaign, product):
    r = client.post(
        "/generate",
        json={"campaign_id": campaign["id"], "product_id": product["id"]},
    )
    assert r.status_code == 401


def test_ab_variant_requires_existing_ad(client, auth_headers):
    r = client.post(
        "/generate/ab-variant",
        json={"advertisement_id": "nonexistent-id"},
        headers=auth_headers,
    )
    assert r.status_code == 404
