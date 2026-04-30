from datetime import datetime

from pydantic import BaseModel


class BrandProfileCreate(BaseModel):
    name: str
    company: str | None = None
    mission: str | None = None
    values: str | None = None
    brand_guidelines: str | None = None
    tone_keywords: str | None = None


class BrandProfileUpdate(BaseModel):
    name: str | None = None
    company: str | None = None
    mission: str | None = None
    values: str | None = None
    brand_guidelines: str | None = None
    tone_keywords: str | None = None


class BrandProfileRead(BaseModel):
    id: str
    user_id: str
    name: str
    company: str | None
    mission: str | None
    values: str | None
    brand_guidelines: str | None
    tone_keywords: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BrandProductCreate(BaseModel):
    name: str
    description: str | None = None


class BrandProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class BrandProductRead(BaseModel):
    id: str
    brand_profile_id: str
    name: str
    description: str | None
    image_path: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BrandPersonaCreate(BaseModel):
    name: str
    traits: str | None = None


class BrandPersonaUpdate(BaseModel):
    name: str | None = None
    traits: str | None = None
    generated_media_url: str | None = None


class BrandPersonaRead(BaseModel):
    id: str
    brand_profile_id: str
    name: str
    traits: str | None
    generated_media_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
