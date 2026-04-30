"""Module tests for the generation router — extends the basic integration tests."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.pipeline.state_keys import (
    AUDIENCE_ANALYSIS,
    BRAND_CONSISTENCY,
    CHANNEL_ADAPTATION,
    COMPETITOR_ANALYSIS,
    CREATIVE_DIRECTIONS,
    EVALUATION_OUTPUT,
    IMAGE_GEN_PROMPT,
    MARKETING_OUTPUT,
    PRODUCT_PROFILE,
    SELECTED_PERSONA,
    TREND_RESEARCH,
)

SAMPLE_PIPELINE_STATE = {
    PRODUCT_PROFILE: {"product_type": "sneaker", "overall_summary": "Fast shoe"},
    AUDIENCE_ANALYSIS: {"primary_audience": {"description": "Runners"}, "mismatch_flags": []},
    TREND_RESEARCH: {"trends": [], "overall_summary": "Minimal data"},
    COMPETITOR_ANALYSIS: {"competitor_themes": [], "whitespace_opportunities": [], "recommended_differentiation": "speed"},
    CREATIVE_DIRECTIONS: {"recommended_headline": "Run Free", "creative_directions": []},
    SELECTED_PERSONA: {"persona": {"name": "Jordan"}, "source": "new"},
    IMAGE_GEN_PROMPT: {
        "image_gen_prompt": "[General Description]\nA sleek ad.\n\n[Quality]\nHigh res.",
        "ab_variant_prompt": "[General Description]\nVariant ad.",
        "ab_change_description": "Different angle",
    },
    MARKETING_OUTPUT: {"product_slogan": "Run Free", "recommended_platforms": ["meta"]},
    EVALUATION_OUTPUT: {"overall_score": 8.5, "dimension_scores": {}, "risks": [], "improvements": [], "verdict": "Strong"},
    CHANNEL_ADAPTATION: {"platform": "meta", "adapted_headline": "Run Free", "adapted_cta": "Buy Now"},
    BRAND_CONSISTENCY: {"consistency_score": 0.92, "violations": [], "approved": True},
}


def _make_mock_runner(pipeline_state: dict):
    agent_map = {
        "product_understanding_agent": PRODUCT_PROFILE,
        "audience_positioning_agent": AUDIENCE_ANALYSIS,
        "trend_critic_agent": TREND_RESEARCH,
        "competitor_agent": COMPETITOR_ANALYSIS,
        "creative_strategy_agent": CREATIVE_DIRECTIONS,
        "persona_agent": SELECTED_PERSONA,
        "prompt_engineering_agent": IMAGE_GEN_PROMPT,
        "marketing_recommendation_agent": MARKETING_OUTPUT,
        "evaluation_agent": EVALUATION_OUTPUT,
        "channel_adaptation_agent": CHANNEL_ADAPTATION,
        "brand_consistency_agent": BRAND_CONSISTENCY,
    }

    class MockEvent:
        def __init__(self, author, state):
            self.author = author
            self._state = state
            self.usage_metadata = None

        def is_final_response(self):
            return True

    class MockSession:
        def __init__(self, state):
            self.state = state

    async def mock_run_async(*args, **kwargs):
        for agent_name in agent_map:
            yield MockEvent(author=agent_name, state=pipeline_state)

    mock = MagicMock()
    mock.run_async = mock_run_async
    mock_session = MockSession({**pipeline_state})
    mock.session_service = AsyncMock()
    mock.session_service.create_session = AsyncMock(return_value=mock_session)
    mock.session_service.get_session = AsyncMock(return_value=mock_session)
    return mock


@pytest.mark.module
def test_cost_summary_event_present_and_numeric(client, auth_headers, campaign, product):
    mock_runner = _make_mock_runner(SAMPLE_PIPELINE_STATE)
    with patch("backend.routers.generation.runner_module.get_runner", return_value=mock_runner):
        r = client.post(
            "/generate",
            json={
                "campaign_id": campaign["id"],
                "product_id": product["id"],
                "target_audience": "Runners aged 20-40",
            },
            headers=auth_headers,
        )
    assert r.status_code == 200

    events = []
    for line in r.text.split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    cost_events = [e for e in events if e.get("event") == "cost_summary"]
    assert len(cost_events) == 1
    ce = cost_events[0]
    assert isinstance(ce.get("total_cost_usd"), (int, float))
    assert isinstance(ce.get("total_latency_ms"), (int, float))
    assert isinstance(ce.get("per_agent"), list)


@pytest.mark.module
def test_all_agent_complete_events_present(client, auth_headers, campaign, product):
    mock_runner = _make_mock_runner(SAMPLE_PIPELINE_STATE)
    with patch("backend.routers.generation.runner_module.get_runner", return_value=mock_runner):
        r = client.post(
            "/generate",
            json={"campaign_id": campaign["id"], "product_id": product["id"]},
            headers=auth_headers,
        )
    events = []
    for line in r.text.split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    agent_events = [e["agent"] for e in events if e.get("event") == "agent_complete"]
    expected_keys = [
        "product_profile", "audience_analysis", "trend_research", "competitor_analysis",
        "creative_directions", "selected_persona", "image_gen_prompt",
        "marketing_output", "evaluation_output", "channel_adaptation", "brand_consistency",
    ]
    for key in expected_keys:
        assert key in agent_events, f"Missing agent_complete event for {key}"


@pytest.mark.module
def test_ab_variant_endpoint_returns_url(client, auth_headers, campaign, product):
    mock_runner = _make_mock_runner(SAMPLE_PIPELINE_STATE)
    with patch("backend.routers.generation.runner_module.get_runner", return_value=mock_runner):
        gen_r = client.post(
            "/generate",
            json={"campaign_id": campaign["id"], "product_id": product["id"]},
            headers=auth_headers,
        )

    events = []
    for line in gen_r.text.split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    done_event = next((e for e in events if e.get("event") == "done"), None)
    assert done_event is not None
    ad_id = done_event["advertisement_id"]

    r = client.post(
        "/generate/ab-variant",
        json={"advertisement_id": ad_id},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert "ab_variant_url" in r.json()
    assert r.json()["ab_variant_url"] is not None


@pytest.mark.module
def test_image_failure_still_returns_done_with_partial_failure(client, auth_headers, campaign, product):
    mock_runner = _make_mock_runner(SAMPLE_PIPELINE_STATE)
    with patch("backend.routers.generation.runner_module.get_runner", return_value=mock_runner):
        with patch(
            "backend.routers.generation.create_image_provider",
            side_effect=RuntimeError("Image API down"),
        ):
            r = client.post(
                "/generate",
                json={"campaign_id": campaign["id"], "product_id": product["id"]},
                headers=auth_headers,
            )

    assert r.status_code == 200
    events = []
    for line in r.text.split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    done_events = [e for e in events if e.get("event") == "done"]
    assert len(done_events) == 1
