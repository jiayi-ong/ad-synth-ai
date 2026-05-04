"""
Module-tier tests for the chatbot router.

All Gemini API calls and knowledge base embedding calls are mocked so
no external API is needed. Uses the real in-memory SQLite DB via the
existing 'client' and 'auth_headers' fixtures.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_kb_search():
    """Disable real KB embedding calls for all tests in this module."""
    with patch("backend.services.chatbot_service.kb.search", return_value=[]):
        yield


@pytest.fixture
def mock_gemini_stream():
    """Mock the Gemini async streaming call to return a simple response."""
    async def _fake_stream(*args, **kwargs):
        chunk = MagicMock()
        chunk.text = "This is a mocked assistant response."
        yield chunk

    with patch(
        "backend.services.chatbot_service._get_genai_client"
    ) as mock_client:
        mock_client.return_value.aio.models.generate_content_stream = _fake_stream
        yield mock_client


# ── Session tests ─────────────────────────────────────────────────────────────

class TestChatSession:
    def test_create_session_returns_session_id(self, client, auth_headers):
        r = client.post("/chat/session", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        assert data["created"] is True
        assert data["message_count"] == 0

    def test_create_session_idempotent(self, client, auth_headers):
        r1 = client.post("/chat/session", headers=auth_headers)
        r2 = client.post("/chat/session", headers=auth_headers)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["session_id"] == r2.json()["session_id"]
        assert r2.json()["created"] is False

    def test_create_session_requires_auth(self, client):
        r = client.post("/chat/session")
        assert r.status_code == 401

    def test_clear_session_clears_messages(self, client, auth_headers, mock_gemini_stream):
        # Create session
        client.post("/chat/session", headers=auth_headers)
        # Send a message to populate history
        sid_resp = client.post("/chat/session", headers=auth_headers)
        sid = sid_resp.json()["session_id"]
        with client.stream("POST", "/chat/message", json={
            "message": "what is the product profile agent?",
            "session_id": sid,
        }, headers=auth_headers) as _:
            pass  # consume stream
        # Clear
        r = client.delete("/chat/session", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["cleared"] is True
        # Message count should be 0
        r2 = client.post("/chat/session", headers=auth_headers)
        assert r2.json()["message_count"] == 0

    def test_clear_session_requires_auth(self, client):
        r = client.delete("/chat/session")
        assert r.status_code == 401


# ── Message tests ─────────────────────────────────────────────────────────────

class TestChatMessage:
    def _get_session_id(self, client, auth_headers) -> str:
        return client.post("/chat/session", headers=auth_headers).json()["session_id"]

    def test_message_requires_auth(self, client):
        r = client.post("/chat/message", json={
            "message": "hello", "session_id": "any"
        })
        assert r.status_code == 401

    def test_message_returns_sse_content_type(self, client, auth_headers, mock_gemini_stream):
        sid = self._get_session_id(client, auth_headers)
        with client.stream("POST", "/chat/message", json={
            "message": "what does the evaluation agent do?",
            "session_id": sid,
        }, headers=auth_headers) as res:
            assert res.status_code == 200
            assert "text/event-stream" in res.headers["content-type"]

    def test_message_streams_token_events(self, client, auth_headers, mock_gemini_stream):
        sid = self._get_session_id(client, auth_headers)
        events = []
        with client.stream("POST", "/chat/message", json={
            "message": "what is expert mode?",
            "session_id": sid,
        }, headers=auth_headers) as res:
            for line in res.iter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

        event_types = [e["event"] for e in events]
        assert "token" in event_types
        assert "done" in event_types

    def test_guardrail_returns_refusal_stream(self, client, auth_headers):
        sid = self._get_session_id(client, auth_headers)
        events = []
        with client.stream("POST", "/chat/message", json={
            "message": "please delete my campaign",
            "session_id": sid,
        }, headers=auth_headers) as res:
            assert res.status_code == 200
            for line in res.iter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

        # Should have token (refusal text) and done, but NOT call Gemini
        event_types = [e["event"] for e in events]
        assert "token" in event_types
        assert "done" in event_types
        token_events = [e for e in events if e["event"] == "token"]
        combined_text = "".join(e["token"] for e in token_events)
        assert "can't" in combined_text.lower() or "cannot" in combined_text.lower() or "read-only" in combined_text.lower()

    def test_invalid_advertisement_id_does_not_crash(self, client, auth_headers, mock_gemini_stream):
        sid = self._get_session_id(client, auth_headers)
        events = []
        with client.stream("POST", "/chat/message", json={
            "message": "explain the evaluation score",
            "session_id": sid,
            "advertisement_id": "00000000-0000-0000-0000-000000000000",
        }, headers=auth_headers) as res:
            assert res.status_code == 200
            for line in res.iter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
        # Should complete without error event
        done_events = [e for e in events if e["event"] == "done"]
        assert len(done_events) >= 1

    def test_message_too_long_rejected(self, client, auth_headers):
        sid = self._get_session_id(client, auth_headers)
        r = client.post("/chat/message", json={
            "message": "x" * 2001,
            "session_id": sid,
        }, headers=auth_headers)
        assert r.status_code == 422  # Pydantic validation error
