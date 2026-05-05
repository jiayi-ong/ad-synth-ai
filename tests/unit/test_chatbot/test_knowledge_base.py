"""Unit tests for chatbot knowledge base loading and similarity search."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import backend.services.knowledge_base as kb_module


SAMPLE_ENTRIES = [
    {"id": "a1", "category": "agent_explanation", "title": "Agent A", "content": "Agent A does X", "tags": ["a"], "related_state_key": "product_profile"},
    {"id": "a2", "category": "ui_howto", "title": "How to B", "content": "To do B, click ...", "tags": ["b"], "related_state_key": None},
    {"id": "a3", "category": "faq", "title": "FAQ C", "content": "FAQ answer C", "tags": ["c"], "related_state_key": "market_segmentation"},
]

SAMPLE_MATRIX = np.array([
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
], dtype=np.float32)


class TestKnowledgeBaseLoad:
    def test_real_json_loads_without_error(self):
        json_path = Path("data/chatbot_knowledge.json")
        if not json_path.exists():
            pytest.skip("chatbot_knowledge.json not present")
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_real_json_entries_have_required_fields(self):
        json_path = Path("data/chatbot_knowledge.json")
        if not json_path.exists():
            pytest.skip("chatbot_knowledge.json not present")
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        for entry in data:
            assert "id" in entry
            assert "category" in entry
            assert "title" in entry
            assert "content" in entry
            assert "tags" in entry
            assert "related_state_key" in entry

    def test_missing_json_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(kb_module, "_KNOWLEDGE_JSON", tmp_path / "nonexistent.json")
        entries = kb_module._load_entries()
        assert entries == []


class TestSimilaritySearch:
    def setup_method(self):
        kb_module._entries = SAMPLE_ENTRIES
        kb_module._matrix = SAMPLE_MATRIX

    def test_top_scoring_entry_returned_first(self):
        # Query vector aligned with entry 0 → score 1.0 for entry 0, 0.0 for others
        q_vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        with patch.object(kb_module, "_embed_query", return_value=q_vec):
            results = kb_module.search("query", top_k=3, threshold=0.5)
        assert results[0]["id"] == "a1"
        assert results[0]["_score"] == pytest.approx(1.0, abs=0.01)

    def test_threshold_filters_low_scores(self):
        # Entry 0 scores 1.0, others score 0.0; threshold 0.9 → only entry 0
        q_vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        with patch.object(kb_module, "_embed_query", return_value=q_vec):
            results = kb_module.search("query", top_k=3, threshold=0.9)
        assert len(results) == 1
        assert results[0]["id"] == "a1"

    def test_top_k_limits_results(self):
        # Uniform vector → all entries score ~0.577; threshold 0.5 → 3 results
        q_vec = np.array([1.0, 1.0, 1.0], dtype=np.float32) / np.sqrt(3)
        with patch.object(kb_module, "_embed_query", return_value=q_vec):
            results = kb_module.search("query", top_k=2, threshold=0.3)
        assert len(results) <= 2

    def test_embedding_failure_returns_empty(self):
        with patch.object(kb_module, "_embed_query", side_effect=RuntimeError("API down")):
            results = kb_module.search("anything")
        assert results == []

    def test_empty_matrix_returns_empty(self):
        kb_module._matrix = np.zeros((0, 3), dtype=np.float32)
        results = kb_module.search("anything")
        assert results == []

    def test_none_matrix_returns_empty(self):
        kb_module._matrix = None
        results = kb_module.search("anything")
        assert results == []


class TestGetEntryByStateKey:
    def setup_method(self):
        kb_module._entries = SAMPLE_ENTRIES

    def test_finds_entry_by_state_key(self):
        entry = kb_module.get_entry_by_state_key("product_profile")
        assert entry is not None
        assert entry["id"] == "a1"

    def test_returns_none_for_unknown_key(self):
        entry = kb_module.get_entry_by_state_key("nonexistent_key")
        assert entry is None

    def test_returns_none_for_null_state_key(self):
        entry = kb_module.get_entry_by_state_key(None)
        assert entry is None
