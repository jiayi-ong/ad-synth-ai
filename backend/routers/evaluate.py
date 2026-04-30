import json
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user
from backend.db.session import get_db
from backend.models.user import User
from backend.pipeline.agents.evaluation_agent import evaluation_agent
from backend.pipeline.standalone_runner import run_agent_with_state
from backend.pipeline.state_keys import (
    AUDIENCE_ANALYSIS,
    BRAND_CONSISTENCY,
    CHANNEL_ADAPTATION,
    COMPETITOR_ANALYSIS,
    CREATIVE_DIRECTIONS,
    EVALUATION_OUTPUT,
    IMAGE_GEN_PROMPT,
    MARKETING_OUTPUT,
    PRODUCT_PROFILE,
    SELECTED_PERSONA,
    TREND_RESEARCH,
)
from backend.schemas.evaluate import EvaluateRequest, EvaluateResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evaluate", tags=["evaluate"])


@router.post("", response_model=EvaluateResponse)
async def evaluate_campaign(
    request: EvaluateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Run strategic evaluation on an existing advertisement or a raw concept.
    Returns a structured critique with scores, risks, and improvement suggestions.
    """
    state: dict = {}

    if request.advertisement_id:
        # Load pipeline state from an existing ad
        from sqlalchemy import select
        from backend.models.advertisement import Advertisement
        from backend.models.campaign import Campaign

        ad = await db.scalar(select(Advertisement).where(Advertisement.id == request.advertisement_id))
        if not ad:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Advertisement not found")

        campaign = await db.scalar(select(Campaign).where(Campaign.id == ad.campaign_id))
        if not campaign or campaign.user_id != current_user.id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Forbidden")

        # Inject pipeline state into evaluation context
        if ad.pipeline_state:
            try:
                stored = json.loads(ad.pipeline_state)
                state.update(stored)
            except (json.JSONDecodeError, TypeError):
                pass

    else:
        # Build minimal state from raw inputs
        state[PRODUCT_PROFILE] = json.dumps({"overall_summary": request.product_description or ""})
        state[AUDIENCE_ANALYSIS] = json.dumps({"overall_summary": request.marketing_brief or ""})
        state[CREATIVE_DIRECTIONS] = json.dumps({"recommended_id": "manual", "scoring_rationale": request.creative_concept or ""})
        state[TREND_RESEARCH] = json.dumps({})
        state[COMPETITOR_ANALYSIS] = json.dumps({})
        state[SELECTED_PERSONA] = json.dumps({})
        state[IMAGE_GEN_PROMPT] = json.dumps({})
        state[MARKETING_OUTPUT] = json.dumps({})

    try:
        result_state = await run_agent_with_state(evaluation_agent, state, user_id=current_user.id)
        raw_output = result_state.get(EVALUATION_OUTPUT, "{}")
        parsed = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
    except Exception as e:
        logger.exception("Evaluation failed: %s", e)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

    return EvaluateResponse(
        overall_score=parsed.get("overall_score", 0.0),
        dimension_scores=parsed.get("dimension_scores", {}),
        risks=parsed.get("risks", []),
        improvements=parsed.get("improvements", []),
        verdict=parsed.get("verdict", ""),
        differentiation_assessment=parsed.get("differentiation_assessment"),
        mismatch_resolution=parsed.get("mismatch_resolution"),
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )
