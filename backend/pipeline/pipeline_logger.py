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

    def log_generation_start(
        self,
        user_id: str,
        product_id: str,
        product_name: str,
        product_description: str,
        campaign_id: str,
        marketing_brief: str,
        target_channel: str | None,
        image_gen_provider: str,
        persona_ids: list[str],
    ) -> None:
        _logger.info(
            json.dumps({
                "event": "generation_start",
                "advertisement_id": self.ad_id,
                "user_id": user_id,
                "campaign_id": campaign_id,
                "product_id": product_id,
                "product_name": product_name,
                "product_description_preview": product_description[:200] if product_description else "",
                "product_description_length": len(product_description) if product_description else 0,
                "marketing_brief": marketing_brief,
                "target_channel": target_channel,
                "image_gen_provider": image_gen_provider,
                "persona_ids": persona_ids,
            })
        )

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

    def log_agent_output(
        self,
        agent_name: str,
        state_key: str,
        parsed_type: str,
        raw_len: int,
        output_summary: dict,
        output_json_preview: str = "",
    ) -> None:
        _logger.info(
            json.dumps({
                "event": "agent_output",
                "advertisement_id": self.ad_id,
                "agent": agent_name,
                "state_key": state_key,
                "parsed_type": parsed_type,
                "raw_len": raw_len,
                "output_json_preview": output_json_preview[:2000] if output_json_preview else "",
                **output_summary,
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
