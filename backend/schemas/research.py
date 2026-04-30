from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ResearchRequest(BaseModel):
    product_description: str
    target_audience: str | None = None
    brand_profile_id: str | None = None
    research_type: Literal["trends", "competitors", "both"] = "both"
    force_refresh: bool = False


class ResearchRead(BaseModel):
    research_id: str
    query_type: str
    query_text: str
    result: dict | None
    created_at: str
    expires_at: str | None
