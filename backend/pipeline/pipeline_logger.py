"""
Structured pipeline event logger.

All records go to the 'pipeline' logger name, which is captured by the
pipeline.log file handler configured in backend.core.logger.setup_logging().
"""
import json
import logging

_logger = logging.getLogger("pipeline")


class PipelineLogger:
    """Emits structured JSON log records for key pipeline lifecycle events."""

    def __init__(self, advertisement_id: str):
        self.ad_id = advertisement_id

    def log_agent_complete(
        self,
        agent_name: str,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        _logger.info(
            json.dumps({
                "event": "agent_complete",
                "advertisement_id": self.ad_id,
                "agent": agent_name,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": round(cost_usd, 6),
            })
        )

    def log_image_generation(
        self,
        provider: str,
        latency_ms: float,
        success: bool,
        error: str | None = None,
    ) -> None:
        record: dict = {
            "event": "image_generation",
            "advertisement_id": self.ad_id,
            "provider": provider,
            "latency_ms": latency_ms,
            "success": success,
        }
        if error:
            record["error"] = error
        _logger.info(json.dumps(record))

    def log_pipeline_complete(
        self,
        user_id: str,
        total_cost_usd: float,
        total_latency_ms: float,
        status: str,
        agent_summary: list[dict],
    ) -> None:
        _logger.info(
            json.dumps({
                "event": "pipeline_complete",
                "advertisement_id": self.ad_id,
                "user_id": user_id,
                "status": status,
                "total_cost_usd": round(total_cost_usd, 6),
                "total_latency_ms": total_latency_ms,
                "agents": agent_summary,
            })
        )
