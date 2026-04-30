from datetime import datetime

from pydantic import BaseModel


class CampaignCreate(BaseModel):
    name: str
    mission: str | None = None
    values: str | None = None
    brand_guidelines: str | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    mission: str | None = None
    values: str | None = None
    brand_guidelines: str | None = None


class CampaignRead(BaseModel):
    id: str
    user_id: str
    name: str
    mission: str | None
    values: str | None
    brand_guidelines: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
