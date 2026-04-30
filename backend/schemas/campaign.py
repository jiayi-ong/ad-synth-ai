from datetime import datetime

from pydantic import BaseModel


class CampaignCreate(BaseModel):
    name: str
    mission: str | None = None
    values: str | None = None
    brand_guidelines: str | None = None
    brand_profile_id: str | None = None
    target_channels: str | None = None  # JSON list e.g. '["meta","tiktok"]'
    campaign_notes: str | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    mission: str | None = None
    values: str | None = None
    brand_guidelines: str | None = None
    brand_profile_id: str | None = None
    target_channels: str | None = None
    campaign_notes: str | None = None


class CampaignRead(BaseModel):
    id: str
    user_id: str
    name: str
    mission: str | None
    values: str | None
    brand_guidelines: str | None
    brand_profile_id: str | None
    target_channels: str | None
    campaign_notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
