import json
import logging
import time
import uuid
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from google.adk.runners import Runner
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.dependencies import get_current_user
from backend.db.session import get_db
from backend.models.advertisement import Advertisement
from backend.models.user import User
from backend.pipeline import runner as runner_module
from backend.pipeline.state_keys import (
    AB_VARIANT_PROMPT,
    AGENT_OUTPUT_KEYS,
    AUDIENCE_ANALYSIS,
    BRAND_CONSISTENCY,
    BRAND_PROFILE_CONTEXT,
    CAMPAIGN_ID,
    CHANNEL_ADAPTATION,
    COMPETITOR_ANALYSIS,
    CREATIVE_DIRECTIONS,
    EVALUATION_OUTPUT,
    EXCLUDED_PERSONA_IDS,
    IMAGE_GEN_PROMPT,
    MARKETING_OUTPUT,
    PIPELINE_ERROR,
    PRODUCT_PROFILE,
    RAW_MARKETING_BRIEF,
    RAW_PRODUCT_DESCRIPTION,
    SELECTED_PERSONA,
    TARGET_CHANNEL,
    TREND_RESEARCH,
)
from backend.pipeline.pipeline_logger import PipelineLogger
from backend.schemas.advertisement import ABVariantRequest, GenerationRequest
from backend.services import advertisement_service
from backend.services.image_service import create_image_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generation"])

# Maps agent name → state key it writes to (determines which SSE events are emitted).
# trend_critic_agent is the inner LlmAgent that writes TREND_RESEARCH; the outer
# trend_research_agent SequentialAgent wrapper does not emit its own final-response event.
_AGENT_KEY_MAP = {
    "product_understanding_agent":   PRODUCT_PROFILE,
    "audience_positioning_agent":    AUDIENCE_ANALYSIS,
    "trend_synthesis_agent":         TREND_RESEARCH,   # final agent in trend_research_pipeline
    "competitor_agent":              COMPETITOR_ANALYSIS,
    "creative_strategy_agent":       CREATIVE_DIRECTIONS,
    "persona_agent":                 SELECTED_PERSONA,
    "prompt_engineering_agent":      IMAGE_GEN_PROMPT,
    "marketing_recommendation_agent": MARKETING_OUTPUT,
    "evaluation_agent":              EVALUATION_OUTPUT,
    "channel_adaptation_agent":      CHANNEL_ADAPTATION,
    "brand_consistency_agent":       BRAND_CONSISTENCY,
}

# Agents whose failure does not stop the rest of the pipeline being surfaced
_NON_CRITICAL_AGENTS = {
    "trend_critic_agent",
    "competitor_agent",
    "marketing_recommendation_agent",
    "evaluation_agent",
    "channel_adaptation_agent",
    "brand_consistency_agent",
}

# Total tracked agent completions for progress bar
_TOTAL_AGENTS = 11

# Gemini 2.0 Flash pricing (USD per million tokens, as of 2025)
_INPUT_COST_PER_M = 0.075
_OUTPUT_COST_PER_M = 0.30


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
        pipeline_start = time.monotonic()
        agent_telemetry: list[dict] = []

        # 1. Create Advertisement record
        ad = await advertisement_service.create_advertisement(
            campaign_id=request.campaign_id,
            product_id=request.product_id,
            persona_ids=request.persona_ids,
            user_id=current_user.id,
            db=db,
        )
        ad_id = ad.id
        pl = PipelineLogger(str(ad_id))
        await advertisement_service.set_ad_status(ad, "running", db)

        # Store channel on the ad record
        if request.target_channel:
            ad.target_channel = request.target_channel
            await db.commit()

        yield _sse("started", {"advertisement_id": ad_id})

        # 2. Build product description + marketing brief
        from sqlalchemy import select
        from backend.models.product import Product
        from backend.models.campaign import Campaign

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

        # 3. Load brand profile context (if campaign links a brand)
        brand_profile_context = ""
        campaign = await db.scalar(select(Campaign).where(Campaign.id == request.campaign_id))
        if campaign and campaign.brand_profile_id:
            from backend.models.brand_profile import BrandProfile
            brand = await db.scalar(select(BrandProfile).where(BrandProfile.id == campaign.brand_profile_id))
            if brand:
                brand_profile_context = json.dumps({
                    "name": brand.name,
                    "company": brand.company,
                    "mission": brand.mission,
                    "values": brand.values,
                    "brand_guidelines": brand.brand_guidelines,
                    "tone_keywords": brand.tone_keywords,
                })
                ad.brand_profile_id = brand.id
                await db.commit()

        # 4. Build initial session state
        initial_state = {
            RAW_PRODUCT_DESCRIPTION: product_desc,
            RAW_MARKETING_BRIEF: marketing_brief,
            CAMPAIGN_ID: request.campaign_id,
            EXCLUDED_PERSONA_IDS: request.excluded_persona_ids,
            BRAND_PROFILE_CONTEXT: brand_profile_context,
            TARGET_CHANNEL: request.target_channel or "",
        }

        # 5. Run ADK pipeline, streaming events
        session_id = f"ad_{ad_id}"
        user_id = current_user.id
        progress = 0

        try:
            runner = runner_module.get_runner()
            await runner.session_service.create_session(
                app_name="ad_synth_ai",
                user_id=user_id,
                session_id=session_id,
                state=initial_state,
            )

            agent_start_times: dict[str, float] = {}

            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text="Generate the advertisement based on the product description and marketing brief in session state.")],
                ),
            ):
                # Track agent start times for telemetry
                if hasattr(event, "author") and event.author and event.author not in agent_start_times:
                    agent_start_times[event.author] = time.monotonic()

                # Detect agent completion events
                if event.is_final_response() and event.author in _AGENT_KEY_MAP:
                    agent_name = event.author
                    state_key = _AGENT_KEY_MAP[agent_name]
                    progress += 1
                    end_time = time.monotonic()
                    start_time = agent_start_times.get(agent_name, end_time)

                    # Collect telemetry
                    input_tokens = 0
                    output_tokens = 0
                    if hasattr(event, "usage_metadata") and event.usage_metadata:
                        input_tokens = getattr(event.usage_metadata, "prompt_token_count", 0) or 0
                        output_tokens = getattr(event.usage_metadata, "candidates_token_count", 0) or 0
                    cost = (input_tokens / 1e6 * _INPUT_COST_PER_M) + (output_tokens / 1e6 * _OUTPUT_COST_PER_M)
                    telemetry_entry = {
                        "agent": agent_name,
                        "latency_ms": round((end_time - start_time) * 1000, 1),
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost_usd": round(cost, 6),
                    }
                    agent_telemetry.append(telemetry_entry)
                    pl.log_agent_complete(
                        agent_name=agent_name,
                        latency_ms=telemetry_entry["latency_ms"],
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_usd=cost,
                    )

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

                    # Special handling: extract specific fields from outputs
                    if state_key == IMAGE_GEN_PROMPT and isinstance(parsed, dict):
                        if parsed.get("image_gen_prompt"):
                            ad.image_gen_prompt = parsed["image_gen_prompt"]
                        if parsed.get("ab_variant_prompt"):
                            ad.ab_variant_prompt = parsed["ab_variant_prompt"]
                        await db.commit()

                    if state_key == MARKETING_OUTPUT and isinstance(parsed, dict):
                        ad.marketing_output = json.dumps(parsed)
                        await db.commit()

                    if state_key == EVALUATION_OUTPUT and isinstance(parsed, dict):
                        ad.evaluation_output = json.dumps(parsed)
                        await db.commit()

                    if state_key == CHANNEL_ADAPTATION and isinstance(parsed, dict):
                        ad.channel_adaptation_output = json.dumps(parsed)
                        await db.commit()

                    if state_key == BRAND_CONSISTENCY and isinstance(parsed, dict):
                        score = parsed.get("consistency_score")
                        if isinstance(score, (int, float)):
                            ad.brand_consistency_score = float(score)
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

        # 6. Trigger image generation
        if ad.image_gen_prompt:
            img_start = time.monotonic()
            try:
                yield _sse("image_generating", {"advertisement_id": ad_id})
                image_provider = create_image_provider()
                image_paths = []
                if product and product.image_path:
                    image_paths = [product.image_path]
                generated = await image_provider.generate(ad.image_gen_prompt, image_paths)
                ad.image_url = generated.url
                img_latency = round((time.monotonic() - img_start) * 1000, 1)
                pl.log_image_generation(
                    provider=settings.image_gen_provider,
                    latency_ms=img_latency,
                    success=True,
                )
                agent_telemetry.append({
                    "agent": "image_generation",
                    "latency_ms": img_latency,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                })

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
                pl.log_image_generation(
                    provider=settings.image_gen_provider,
                    latency_ms=round((time.monotonic() - img_start) * 1000, 1),
                    success=False,
                    error=str(e),
                )
                yield _sse("error", {"agent": "image_generation", "data": {"message": str(e)}})

        # 7. Persist telemetry and finalize
        total_cost = sum(t["cost_usd"] for t in agent_telemetry)
        total_latency = round((time.monotonic() - pipeline_start) * 1000, 1)
        await advertisement_service.update_pipeline_state(
            ad, "_telemetry",
            {"agents": agent_telemetry, "total_cost_usd": round(total_cost, 6), "total_latency_ms": total_latency},
            db,
        )

        final_status = "completed" if ad.status != "partial_failure" else "partial_failure"
        if not ad.image_url:
            final_status = "partial_failure"
        await advertisement_service.set_ad_status(ad, final_status, db)
        pl.log_pipeline_complete(
            user_id=str(user_id),
            total_cost_usd=total_cost,
            total_latency_ms=total_latency,
            status=final_status,
            agent_summary=agent_telemetry,
        )
        yield _sse("done", {"advertisement_id": ad_id, "status": final_status})
        yield _sse("cost_summary", {
            "total_cost_usd": round(total_cost, 6),
            "total_latency_ms": total_latency,
            "per_agent": agent_telemetry,
        })

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
