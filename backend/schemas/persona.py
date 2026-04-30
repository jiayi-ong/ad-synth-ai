from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PersonaCreate(BaseModel):
    name: str
    traits: dict[str, Any] | None = None
    exclusion_rules: list[str] | None = None


class PersonaUpdate(BaseModel):
    name: str | None = None
    traits: dict[str, Any] | None = None
    exclusion_rules: list[str] | None = None
    generated_media_url: str | None = None


class PersonaRead(BaseModel):
    id: str
    campaign_id: str
    name: str
    traits: dict[str, Any] | None
    generated_media_url: str | None
    usage_history: list[str] | None
    exclusion_rules: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}
