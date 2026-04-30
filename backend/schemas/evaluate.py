from datetime import datetime

from pydantic import BaseModel


class EvaluateRequest(BaseModel):
    campaign_id: str | None = None
    advertisement_id: str | None = None  # evaluate existing ad's pipeline state
    # Alternative: evaluate a concept without a full pipeline run
    product_description: str | None = None
    marketing_brief: str | None = None
    creative_concept: str | None = None


class EvaluateResponse(BaseModel):
    overall_score: float
    dimension_scores: dict[str, float]
    risks: list[dict]
    improvements: list[dict]
    verdict: str
    differentiation_assessment: str | None = None
    mismatch_resolution: str | None = None
    evaluated_at: str
