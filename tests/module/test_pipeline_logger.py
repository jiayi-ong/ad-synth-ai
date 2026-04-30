"""Module tests for PipelineLogger structured logging."""
import json
import logging
from pathlib import Path

import pytest

from backend.pipeline.pipeline_logger import PipelineLogger


@pytest.fixture(autouse=True)
def _restore_pipeline_logger():
    """Restore the 'pipeline' logger to its original state after each test."""
    pl = logging.getLogger("pipeline")
    original_handlers = pl.handlers[:]
    original_propagate = pl.propagate
    original_level = pl.level
    yield
    pl.handlers.clear()
    for h in original_handlers:
        pl.addHandler(h)
    pl.propagate = original_propagate
    pl.setLevel(original_level)


def _setup_pipeline_file_log(tmp_path: Path) -> Path:
    """Configure the 'pipeline' logger to write to a temp file and return its path."""
    log_file = tmp_path / "pipeline_test.log"
    handler = logging.FileHandler(str(log_file), encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("pipeline")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return log_file


def _read_log_records(log_file: Path) -> list[dict]:
    records = []
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


@pytest.mark.module
def test_log_agent_complete_writes_record(tmp_path):
    log_file = _setup_pipeline_file_log(tmp_path)
    pl = PipelineLogger("ad-001")
    pl.log_agent_complete(
        agent_name="product_understanding_agent",
        latency_ms=1234.5,
        input_tokens=500,
        output_tokens=200,
        cost_usd=0.000123,
    )
    records = _read_log_records(log_file)
    assert len(records) == 1
    r = records[0]
    assert r["event"] == "agent_complete"
    assert r["advertisement_id"] == "ad-001"
    assert r["agent"] == "product_understanding_agent"
    assert r["latency_ms"] == 1234.5
    assert r["input_tokens"] == 500
    assert r["output_tokens"] == 200
    assert "cost_usd" in r


@pytest.mark.module
def test_log_pipeline_complete_writes_summary(tmp_path):
    log_file = _setup_pipeline_file_log(tmp_path)
    pl = PipelineLogger("ad-002")
    pl.log_pipeline_complete(
        user_id="user-xyz",
        total_cost_usd=0.05,
        total_latency_ms=12000.0,
        status="completed",
        agent_summary=[{"agent": "product_understanding_agent", "latency_ms": 500.0}],
    )
    records = _read_log_records(log_file)
    assert len(records) == 1
    r = records[0]
    assert r["event"] == "pipeline_complete"
    assert r["advertisement_id"] == "ad-002"
    assert r["user_id"] == "user-xyz"
    assert r["status"] == "completed"
    assert r["total_latency_ms"] == 12000.0
    assert len(r["agents"]) == 1


@pytest.mark.module
def test_log_image_generation_success(tmp_path):
    log_file = _setup_pipeline_file_log(tmp_path)
    pl = PipelineLogger("ad-003")
    pl.log_image_generation(provider="gemini", latency_ms=2500.0, success=True)
    records = _read_log_records(log_file)
    assert len(records) == 1
    r = records[0]
    assert r["event"] == "image_generation"
    assert r["success"] is True
    assert r["provider"] == "gemini"
    assert "error" not in r


@pytest.mark.module
def test_log_image_generation_failure(tmp_path):
    log_file = _setup_pipeline_file_log(tmp_path)
    pl = PipelineLogger("ad-004")
    pl.log_image_generation(provider="vertexai", latency_ms=100.0, success=False, error="Quota exceeded")
    records = _read_log_records(log_file)
    assert len(records) == 1
    r = records[0]
    assert r["success"] is False
    assert r["error"] == "Quota exceeded"


@pytest.mark.module
def test_multiple_agent_logs_ordered(tmp_path):
    log_file = _setup_pipeline_file_log(tmp_path)
    pl = PipelineLogger("ad-005")
    agents = ["product_understanding_agent", "audience_positioning_agent", "trend_critic_agent"]
    for agent in agents:
        pl.log_agent_complete(agent_name=agent, latency_ms=100.0, input_tokens=100, output_tokens=50, cost_usd=0.001)
    records = _read_log_records(log_file)
    assert len(records) == 3
    assert [r["agent"] for r in records] == agents
