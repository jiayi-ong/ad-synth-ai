import json
import logging
import uuid
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from google.adk.runners import Runner
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user
from backend.db.session import get_db
from backend.models.advertisement import Advertisement
from backend.models.user import User
from backend.pipeline import runner as runner_module
from backend.pipeline.state_keys import (
    AB_VARIANT_PROMPT,
    AGENT_OUTPUT_KEYS,
    AUDIENCE_ANALYSIS,
    CAMPAIGN_ID,
    CREATIVE_DIRECTIONS,
    EXCLUDED_PERSONA_IDS,
    IMAGE_GEN_PROMPT,
    MARKETING_OUTPUT,
    PIPELINE_ERROR,
    PRODUCT_PROFILE,
    RAW_MARKETING_BRIEF,
    RAW_PRODUCT_DESCRIPTION,
    SELECTED_PERSONA,
    TREND_RESEARCH,
)
from backend.schemas.advertisement import ABVariantRequest, GenerationRequest
from backend.services import advertisement_service
from backend.services.image_service import create_image_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generation"])

# Maps agent name → state key it writes to
_AGENT_KEY_MAP = {
    "product_understanding_agent": PRODUCT_PROFILE,
    "audience_positioning_agent": AUDIENCE_ANALYSIS,
    "trend_research_agent": TREND_RESEARCH,
    "creative_strategy_agent": CREATIVE_DIRECTIONS,
    "persona_agent": SELECTED_PERSONA,
    "prompt_engineering_agent": IMAGE_GEN_PROMPT,
    "marketing_recommendation_agent": MARKETING_OUTPUT,
}

# Agents that can fail without stopping the rest of the pipeline
_NON_CRITICAL_AGENTS = {"trend_research_agent", "marketing_recommendation_agent"}

# Total agent count for progress reporting
_TOTAL_AGENTS = 7


def _sse(event: str, data: dict) -> str:
    return f"data: {json.dumps({'event': event, **data})}\n\n"


def _parse_json_output(raw: str | None) -> dict | str:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw or {}


@router.post("")
async def generate_ad(
    request: GenerationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    async def event_stream() -> AsyncGenerator[str, None]:
        # 1. Create Advertisement record
        ad = await advertisement_service.create_advertisement(
            campaign_id=request.campaign_id,
            product_id=request.product_id,
            persona_ids=request.persona_ids,
            user_id=current_user.id,
            db=db,
        )
        ad_id = ad.id
        await advertisement_service.set_ad_status(ad, "running", db)
        yield _sse("started", {"advertisement_id": ad_id})

        # 2. Build product description + marketing brief for pipeline inputs
        from sqlalchemy import select
        from backend.models.product import Product
        product = await db.scalar(select(Product).where(Product.id == request.product_id))
        product_desc = f"{product.name}\n{product.description or ''}" if product else ""

        brief_parts = []
        if request.target_audience:
            brief_parts.append(f"Target audience: {request.target_audience}")
        if request.value_proposition:
            brief_parts.append(f"Value proposition: {request.value_proposition}")
        if request.positioning:
            brief_parts.append(f"Positioning: {request.positioning}")
        if request.tone:
            brief_parts.append(f"Tone: {request.tone}")
        if request.extra_notes:
            brief_parts.append(f"Notes: {request.extra_notes}")
        marketing_brief = "\n".join(brief_parts)

        # 3. Build initial session state
        initial_state = {
            RAW_PRODUCT_DESCRIPTION: product_desc,
            RAW_MARKETING_BRIEF: marketing_brief,
            CAMPAIGN_ID: request.campaign_id,
            EXCLUDED_PERSONA_IDS: request.excluded_persona_ids,
        }

        # 4. Run ADK pipeline, streaming events
        runner = runner_module.get_runner()
        session_id = f"ad_{ad_id}"
        user_id = current_user.id
        progress = 0
        completed_agent_keys: set[str] = set()

        try:
            session = await runner.session_service.create_session(
                app_name="ad_synth_ai",
                user_id=user_id,
                session_id=session_id,
                state=initial_state,
            )

            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text="Generate the advertisement based on the product description and marketing brief in session state.")],
                ),
            ):
                # Detect agent completion events
                if event.is_final_response() and event.author in _AGENT_KEY_MAP:
                    agent_name = event.author
                    state_key = _AGENT_KEY_MAP[agent_name]
                    progress += 1

                    # Retrieve the agent's output from session state
                    current_session = await runner.session_service.get_session(
                        app_name="ad_synth_ai",
                        user_id=user_id,
                        session_id=session_id,
                    )
                    raw_output = current_session.state.get(state_key, "")
                    parsed = _parse_json_output(raw_output)

                    # Persist to DB
                    await advertisement_service.update_pipeline_state(ad, state_key, parsed, db)
                    completed_agent_keys.add(state_key)

                    # Special handling: extract image_gen_prompt and ab_variant_prompt
                    if state_key == IMAGE_GEN_PROMPT and isinstance(parsed, dict):
                        prompt_text = parsed.get("image_gen_prompt", "")
                        ab_prompt = parsed.get("ab_variant_prompt", "")
                        if prompt_text:
                            ad.image_gen_prompt = prompt_text
                        if ab_prompt:
                            ad.ab_variant_prompt = ab_prompt
                        await db.commit()

                    if state_key == MARKETING_OUTPUT and isinstance(parsed, dict):
                        ad.marketing_output = json.dumps(parsed)
                        await db.commit()

                    yield _sse("agent_complete", {
                        "agent": state_key,
                        "data": parsed,
                        "progress": progress,
                        "total": _TOTAL_AGENTS,
                        "advertisement_id": ad_id,
                    })

        except Exception as e:
            logger.exception("Pipeline error for ad %s: %s", ad_id, e)
            await advertisement_service.set_ad_status(ad, "partial_failure", db)
            await advertisement_service.update_pipeline_state(ad, PIPELINE_ERROR, {"message": str(e)}, db)
            yield _sse("error", {"agent": "pipeline", "data": {"message": str(e)}})

        # 5. Trigger image generation
        if ad.image_gen_prompt:
            try:
                yield _sse("image_generating", {"advertisement_id": ad_id})
                image_provider = create_image_provider()
                image_paths = []
                if product and product.image_path:
                    image_paths = [product.image_path]
                generated = await image_provider.generate(ad.image_gen_prompt, image_paths)
                ad.image_url = generated.url

                # Also generate A/B variant image if prompt exists
                ab_url = None
                if ad.ab_variant_prompt:
                    ab_generated = await image_provider.generate(ad.ab_variant_prompt, image_paths)
                    ad.ab_variant_url = ab_generated.url
                    ab_url = ab_generated.url

                await db.commit()
                yield _sse("image_ready", {
                    "data": {"url": generated.url, "variant_url": ab_url},
                    "advertisement_id": ad_id,
                })
            except Exception as e:
                logger.exception("Image generation failed for ad %s: %s", ad_id, e)
                yield _sse("error", {"agent": "image_generation", "data": {"message": str(e)}})

        # 6. Finalize
        final_status = "completed" if not ad.status == "partial_failure" else "partial_failure"
        if not ad.image_url:
            final_status = "partial_failure"
        await advertisement_service.set_ad_status(ad, final_status, db)
        yield _sse("done", {"advertisement_id": ad_id, "status": final_status})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/ab-variant")
async def generate_ab_variant(
    request: ABVariantRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from sqlalchemy import select
    from backend.models.campaign import Campaign

    ad = await db.scalar(select(Advertisement).where(Advertisement.id == request.advertisement_id))
    if not ad:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Advertisement not found")

    # Verify ownership via campaign
    campaign = await db.scalar(select(Campaign).where(Campaign.id == ad.campaign_id))
    if not campaign or campaign.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden")

    if not ad.ab_variant_prompt:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No A/B variant prompt available for this advertisement")

    image_provider = create_image_provider()
    generated = await image_provider.generate(ad.ab_variant_prompt, [])
    ad.ab_variant_url = generated.url
    await db.commit()

    return {"ab_variant_url": generated.url, "advertisement_id": ad.id}
