"""Unit tests for chatbot service logic (no DB or LLM calls)."""
import json

import pytest

from backend.services.chatbot_service import (
    _build_system_prompt,
    _extract_pipeline_context,
    _format_kb_entries,
    _truncate_messages,
    check_guardrail,
)


class TestTruncation:
    def test_truncates_when_at_limit(self, monkeypatch):
        monkeypatch.setattr("backend.services.chatbot_service.settings.chatbot_max_turns", 2)
        messages = [
            {"role": "user", "content": "q1", "timestamp": "t"},
            {"role": "assistant", "content": "a1", "timestamp": "t"},
            {"role": "user", "content": "q2", "timestamp": "t"},
            {"role": "assistant", "content": "a2", "timestamp": "t"},
        ]
        result = _truncate_messages(messages)
        # max_entries = 2*2 = 4; 4 messages exactly at limit → no truncation
        assert len(result) == 4

    def test_truncates_when_over_limit(self, monkeypatch):
        monkeypatch.setattr("backend.services.chatbot_service.settings.chatbot_max_turns", 2)
        messages = [
            {"role": "user", "content": "q1", "timestamp": "t"},
            {"role": "assistant", "content": "a1", "timestamp": "t"},
            {"role": "user", "content": "q2", "timestamp": "t"},
            {"role": "assistant", "content": "a2", "timestamp": "t"},
            {"role": "user", "content": "q3", "timestamp": "t"},
            {"role": "assistant", "content": "a3", "timestamp": "t"},
        ]
        result = _truncate_messages(messages)
        # max_entries=4; 6 messages → drop oldest 2 → 4 remain
        assert len(result) == 4
        assert result[0]["content"] == "q2"

    def test_no_truncation_below_limit(self, monkeypatch):
        monkeypatch.setattr("backend.services.chatbot_service.settings.chatbot_max_turns", 10)
        messages = [{"role": "user", "content": f"q{i}", "timestamp": "t"} for i in range(5)]
        result = _truncate_messages(messages)
        assert len(result) == 5

    def test_empty_list_unchanged(self, monkeypatch):
        monkeypatch.setattr("backend.services.chatbot_service.settings.chatbot_max_turns", 5)
        assert _truncate_messages([]) == []


class TestFormatKbEntries:
    def test_no_entries_returns_placeholder(self):
        result = _format_kb_entries([])
        assert "No specific knowledge base" in result

    def test_formats_entry_title_and_content(self):
        entries = [{"title": "Agent A", "content": "Does X", "related_state_key": "product_profile"}]
        result = _format_kb_entries(entries)
        assert "Agent A" in result
        assert "Does X" in result

    def test_truncates_long_content(self):
        long_content = "x" * 1000
        entries = [{"title": "T", "content": long_content, "related_state_key": None}]
        result = _format_kb_entries(entries)
        assert len(result) < 1000
        assert "…" in result

    def test_multiple_entries_separated(self):
        entries = [
            {"title": "Entry 1", "content": "Content 1", "related_state_key": None},
            {"title": "Entry 2", "content": "Content 2", "related_state_key": None},
        ]
        result = _format_kb_entries(entries)
        assert "Entry 1" in result
        assert "Entry 2" in result


class TestExtractPipelineContext:
    def test_extracts_relevant_section(self):
        state = {
            "product_profile": json.dumps({"summary": "A running shoe", "features": ["fast", "light"]}),
            "market_segmentation": json.dumps({"segments": ["runners", "athletes"]}),
        }
        kb_entries = [{"related_state_key": "product_profile", "title": "T"}]
        result = _extract_pipeline_context(state, kb_entries)
        assert "product_profile" in result
        assert "running shoe" in result

    def test_no_relevant_keys_falls_back_to_defaults(self):
        state = {
            "marketing_output": json.dumps({"copy": "Great product!"}),
            "evaluation_output": json.dumps({"score": 0.9}),
        }
        kb_entries = []  # no related_state_keys → falls back to defaults
        result = _extract_pipeline_context(state, kb_entries)
        # Should include one of the default keys
        assert any(k in result for k in ("marketing_output", "evaluation_output", "creative_directions"))

    def test_returns_empty_when_no_matching_keys_in_state(self):
        state = {"trend_research": json.dumps({"trends": []})}
        kb_entries = [{"related_state_key": "product_profile", "title": "T"}]
        result = _extract_pipeline_context(state, kb_entries)
        assert result == ""

    def test_truncates_total_to_max_chars(self):
        big_content = "x" * 3000
        state = {"product_profile": json.dumps({"data": big_content})}
        kb_entries = [{"related_state_key": "product_profile", "title": "T"}]
        result = _extract_pipeline_context(state, kb_entries)
        assert len(result) <= 2100  # _MAX_PIPELINE_TOTAL_CHARS + header overhead

    def test_no_advertisement_id_no_context(self):
        result = _extract_pipeline_context({}, [])
        assert result == ""


class TestBuildSystemPrompt:
    def test_contains_kb_context(self):
        kb_entries = [{"title": "My Agent", "content": "It does Z", "related_state_key": None}]
        prompt = _build_system_prompt(kb_entries, "")
        assert "My Agent" in prompt
        assert "It does Z" in prompt

    def test_contains_pipeline_context_when_provided(self):
        kb_entries = []
        pipeline_ctx = "CURRENT AD PIPELINE OUTPUTS:\n[product_profile]\n{...}"
        prompt = _build_system_prompt(kb_entries, pipeline_ctx)
        assert "CURRENT AD PIPELINE OUTPUTS" in prompt

    def test_no_pipeline_context_empty_section(self):
        kb_entries = []
        prompt = _build_system_prompt(kb_entries, "")
        assert "CURRENT AD PIPELINE OUTPUTS" not in prompt

    def test_contains_current_date(self):
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        prompt = _build_system_prompt([], "")
        assert today in prompt
