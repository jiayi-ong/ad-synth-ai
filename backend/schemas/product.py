from datetime import datetime

from pydantic import BaseModel


class ProductCreate(BaseModel):
    name: str
    description: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ProductRead(BaseModel):
    id: str
    campaign_id: str
    name: str
    description: str | None
    image_path: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
