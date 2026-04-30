"""System tests — full end-to-end pipeline with real Gemini LLM.

Requires GOOGLE_API_KEY to be set and GOOGLE_GENAI_USE_VERTEXAI=FALSE.
Uses IMAGE_GEN_PROVIDER=mock so no image generation API is needed.

These tests are slow (30-120 seconds each) and consume Gemini quota.
Run with: bash scripts/run_tests.sh system
"""
import json
import os

import pytest

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

pytestmark = pytest.mark.system


def _skip_if_no_gemini():
    if not GOOGLE_API_KEY:
        pytest.skip("GOOGLE_API_KEY not set — skipping full pipeline system test")


@pytest.fixture(autouse=True)
def require_gemini_key():
    _skip_if_no_gemini()


def _parse_sse_events(response_text: str) -> list[dict]:
    events = []
    for line in response_text.split("\n"):
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


def test_full_generation_pipeline_completes(client, auth_headers, campaign, product):
    """Full pipeline: 11 agents run via real Gemini, mock image returned."""
    r = client.post(
        "/generate",
        json={
            "campaign_id": campaign["id"],
            "product_id": product["id"],
            "target_audience": "Athletes aged 25-35 who prioritize performance",
            "value_proposition": "Lightest running shoe on the market",
            "tone": "energetic and motivational",
        },
        headers=auth_headers,
        timeout=180,
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]

    events = _parse_sse_events(r.text)
    event_types = [e.get("event") for e in events]

    assert "started" in event_types, "Missing 'started' event"
    assert "done" in event_types, "Missing 'done' event"

    done_event = next(e for e in events if e.get("event") == "done")
    assert done_event["status"] in ("completed", "partial_failure")

    # Verify at least some agent_complete events
    agent_complete_events = [e for e in events if e.get("event") == "agent_complete"]
    assert len(agent_complete_events) > 0, "No agent_complete events received"

    # Verify mock image was generated (pipeline.log should show it)
    assert "image_ready" in event_types or "image_generating" in event_types


def test_full_pipeline_cost_summary(client, auth_headers, campaign, product):
    """Verify cost_summary event with real token counts from Gemini."""
    r = client.post(
        "/generate",
        json={
            "campaign_id": campaign["id"],
            "product_id": product["id"],
            "target_audience": "Tech professionals",
        },
        headers=auth_headers,
        timeout=180,
    )
    assert r.status_code == 200
    events = _parse_sse_events(r.text)

    cost_events = [e for e in events if e.get("event") == "cost_summary"]
    assert len(cost_events) == 1
    ce = cost_events[0]
    assert isinstance(ce["total_cost_usd"], (int, float))
    assert isinstance(ce["total_latency_ms"], (int, float))
    assert ce["total_latency_ms"] > 0


def test_pipeline_creates_log_entries(client, auth_headers, campaign, product, tmp_path, monkeypatch):
    """Verify pipeline.log receives structured records during a real run."""
    import logging
    from pathlib import Path

    # Redirect pipeline logger to a temp file for this test
    log_file = tmp_path / "pipeline.log"
    handler = logging.FileHandler(str(log_file), encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    pl_logger = logging.getLogger("pipeline")
    original_handlers = pl_logger.handlers[:]
    pl_logger.handlers.clear()
    pl_logger.addHandler(handler)
    pl_logger.setLevel(logging.DEBUG)
    pl_logger.propagate = False

    try:
        r = client.post(
            "/generate",
            json={"campaign_id": campaign["id"], "product_id": product["id"]},
            headers=auth_headers,
            timeout=180,
        )
        assert r.status_code == 200
        handler.flush()

        records = []
        for line in log_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        assert len(records) > 0, "Pipeline log file is empty after full run"

        event_types = [r.get("event") for r in records]
        assert "agent_complete" in event_types
        assert "pipeline_complete" in event_types

    finally:
        pl_logger.handlers.clear()
        for h in original_handlers:
            pl_logger.addHandler(h)
