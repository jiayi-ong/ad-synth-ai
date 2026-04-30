from datetime import datetime
from typing import Any

from pydantic import BaseModel


class GenerationRequest(BaseModel):
    campaign_id: str
    product_id: str
    persona_ids: list[str] = []
    excluded_persona_ids: list[str] = []
    # Additional marketing inputs supplied by user
    target_audience: str | None = None
    value_proposition: str | None = None
    positioning: str | None = None
    tone: str | None = None
    extra_notes: str | None = None
    # Channel for platform-specific adaptation
    target_channel: str | None = None  # "meta"|"tiktok"|"youtube"|None
    # Output format (image default; video is a scaffold for future use)
    output_format: str = "image"  # "image"|"video"


class ABVariantRequest(BaseModel):
    advertisement_id: str


class AdvertisementRead(BaseModel):
    id: str
    campaign_id: str
    product_id: str
    persona_ids: list[str] | None
    status: str
    pipeline_state: dict[str, Any] | None
    image_gen_prompt: str | None
    image_url: str | None
    ab_variant_prompt: str | None
    ab_variant_url: str | None
    marketing_output: dict[str, Any] | None
    # New fields
    target_channel: str | None
    evaluation_output: dict[str, Any] | None
    channel_adaptation_output: dict[str, Any] | None
    brand_consistency_score: float | None
    brand_profile_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
