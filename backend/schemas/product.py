from datetime import datetime

from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    unit_cost_usd: float | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    unit_cost_usd: float | None = None


class ProductRead(BaseModel):
    id: str
    campaign_id: str
    name: str
    description: str | None
    unit_cost_usd: float | None
    image_path: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
