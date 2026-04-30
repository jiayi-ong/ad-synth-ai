"""Unit tests for the centralized logging setup."""
import json
import logging
from pathlib import Path

import pytest

from backend.core.config import Settings


@pytest.fixture(autouse=True)
def restore_root_logging():
    """Save and restore root logger and pipeline logger state between tests."""
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level

    # The pipeline logger may have propagation disabled by test_pipeline_logger.py
    pl = logging.getLogger("pipeline")
    original_pl_handlers = pl.handlers[:]
    original_pl_propagate = pl.propagate

    yield

    root.handlers.clear()
    for h in original_handlers:
        root.addHandler(h)
    root.setLevel(original_level)

    pl.handlers.clear()
    for h in original_pl_handlers:
        pl.addHandler(h)
    pl.propagate = original_pl_propagate


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        _env_file=None,
        log_level="DEBUG",
        log_format="json",
        log_to_file=True,
    )
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.mark.unit
def test_setup_logging_creates_file_handlers(tmp_path):
    from backend.core.logger import setup_logging
    s = _make_settings(log_dir=str(tmp_path))
    setup_logging(s)

    root = logging.getLogger()
    file_paths = set()
    for h in root.handlers:
        if hasattr(h, "baseFilename"):
            file_paths.add(Path(h.baseFilename).name)

    assert "app.log" in file_paths
    assert "pipeline.log" in file_paths
    assert "api.log" in file_paths


@pytest.mark.unit
def test_setup_logging_skips_file_handlers_when_disabled(tmp_path):
    from backend.core.logger import setup_logging
    s = _make_settings(log_dir=str(tmp_path), log_to_file=False)
    setup_logging(s)

    root = logging.getLogger()
    file_handlers = [h for h in root.handlers if hasattr(h, "baseFilename")]
    assert len(file_handlers) == 0


@pytest.mark.unit
def test_json_formatter_produces_valid_json(tmp_path):
    from backend.core.logger import setup_logging
    s = _make_settings(log_dir=str(tmp_path))
    setup_logging(s)

    test_logger = logging.getLogger("test.json_formatter")
    test_logger.info("hello json world")

    app_log = tmp_path / "app.log"
    assert app_log.exists()
    lines = [l for l in app_log.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) > 0
    for line in lines:
        parsed = json.loads(line)
        assert "timestamp" in parsed
        assert "level" in parsed
        assert "logger" in parsed
        assert "message" in parsed


@pytest.mark.unit
def test_pipeline_log_captures_only_pipeline_logger(tmp_path):
    from backend.core.logger import setup_logging
    s = _make_settings(log_dir=str(tmp_path))
    setup_logging(s)

    logging.getLogger("pipeline").info("pipeline event")
    logging.getLogger("other.module").info("other event")

    pipeline_log = tmp_path / "pipeline.log"
    assert pipeline_log.exists()
    content = pipeline_log.read_text(encoding="utf-8")
    assert "pipeline event" in content
    assert "other event" not in content


@pytest.mark.unit
def test_log_dir_created_if_missing(tmp_path):
    from backend.core.logger import setup_logging
    new_dir = tmp_path / "new_logs_subdir"
    assert not new_dir.exists()
    s = _make_settings(log_dir=str(new_dir))
    setup_logging(s)
    assert new_dir.exists()
