"""
Centralized logging setup.

Configures:
  - Console handler (text or JSON based on LOG_FORMAT)
  - Rotating file handler → logs/app.log   (all logs, always JSON)
  - Rotating file handler → logs/pipeline.log  (pipeline.* loggers only)
  - Rotating file handler → logs/api.log   (HTTP request events only)

Set LOG_TO_FILE=false to disable file handlers (recommended for Cloud Run
where stdout is ingested by Cloud Logging directly).
"""
import json
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.core.config import Settings

_10_MB = 10 * 1024 * 1024
_BACKUP_COUNT = 5


class _JsonFormatter(logging.Formatter):
    """Formats each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        # Carry through any extra fields attached via logger.info("...", extra={...})
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            }:
                entry[key] = value
        return json.dumps(entry, default=str)


class _PipelineFilter(logging.Filter):
    """Passes only records from loggers whose name starts with 'pipeline'."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith("pipeline")


class _ApiFilter(logging.Filter):
    """Passes only HTTP request log records (emitted by ObservabilityMiddleware)."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            data = json.loads(record.getMessage())
            return data.get("type") == "http_request"
        except (json.JSONDecodeError, AttributeError):
            return False


def _make_rotating_handler(path: Path, log_filter: logging.Filter | None = None) -> logging.Handler:
    handler = logging.handlers.RotatingFileHandler(
        path, maxBytes=_10_MB, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(_JsonFormatter())
    if log_filter:
        handler.addFilter(log_filter)
    return handler


def setup_logging(settings: "Settings") -> None:
    """
    Configure the root logger and optional file handlers.
    Call once at application startup (replaces logging.basicConfig).
    """
    level = getattr(logging, settings.log_level, logging.INFO)

    # Console handler
    console = logging.StreamHandler()
    if settings.log_format == "json":
        console.setFormatter(_JsonFormatter())
    else:
        console.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )

    root = logging.getLogger()
    root.setLevel(level)
    # Clear any handlers added by earlier basicConfig calls
    root.handlers.clear()
    root.addHandler(console)

    if not settings.log_to_file:
        return

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # app.log — everything
    root.addHandler(_make_rotating_handler(log_dir / "app.log"))

    # pipeline.log — pipeline.* loggers only
    pipeline_handler = _make_rotating_handler(log_dir / "pipeline.log", _PipelineFilter())
    root.addHandler(pipeline_handler)

    # api.log — HTTP request events only
    api_handler = _make_rotating_handler(log_dir / "api.log", _ApiFilter())
    root.addHandler(api_handler)
