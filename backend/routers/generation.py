import asyncio
import json
import logging
import time
import uuid
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
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
    CAMPAIGN_ARCHITECTURE,
    CAMPAIGN_ID,
    CHANNEL_ADAPTATION,
    COMPETITOR_ANALYSIS,
    CREATIVE_DIRECTIONS,
    DOWNSTREAM_KEYS,
    EVALUATION_OUTPUT,
    EXCLUDED_PERSONA_IDS,
    EXPERIMENT_DESIGN,
    EXTRA_INPUT,
    IMAGE_GEN_PROMPT,
    LOOP_EVAL_SIGNAL,
    LOOP_FEEDBACK,
    MARKET_SEGMENTATION,
    MARKETING_OUTPUT,
    PIPELINE_ERROR,
    PRICING_ANALYSIS,
    PRODUCT_PROFILE,
    RAW_MARKETING_BRIEF,
    RAW_PRODUCT_DESCRIPTION,
    SELECTED_PERSONA,
    TARGET_CHANNEL,
    TREND_RESEARCH,
)
from backend.pipeline.pipeline_logger import PipelineLogger
from backend.schemas.advertisement import ABVariantRequest, GenerationRequest, RerunStageRequest
from backend.services import advertisement_service
from backend.services.image_service import create_image_provider

# Module-level cancellation flags keyed by advertisement_id
_cancellation_flags: dict[str, asyncio.Event] = {}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generation"])

# Maps agent name → state key it writes to (determines which SSE events are emitted).
# trend_validator_agent is the final agent in the trend sub-pipeline; it reads and
# validates the synthesis output then writes the corrected version to TREND_RESEARCH.
# trend_synthesis_agent is intentionally omitted — the validator's corrected output
# supersedes it, so we emit only one SSE event for trend_research.
_AGENT_KEY_MAP = {
    "product_understanding_agent":    PRODUCT_PROFILE,
    "market_segmentation_agent":      MARKET_SEGMENTATION,
    "audience_positioning_agent":     AUDIENCE_ANALYSIS,
    "loop_evaluator_agent":           LOOP_EVAL_SIGNAL,   # internal loop signal, no UI tab
    "trend_validator_agent":          TREND_RESEARCH,
    "competitor_agent":               COMPETITOR_ANALYSIS,
    "pricing_analysis_agent":         PRICING_ANALYSIS,
    "creative_strategy_agent":        CREATIVE_DIRECTIONS,
    "persona_agent":                  SELECTED_PERSONA,
    "prompt_engineering_agent":       IMAGE_GEN_PROMPT,
    "campaign_architecture_agent":    CAMPAIGN_ARCHITECTURE,
    "experiment_design_agent":        EXPERIMENT_DESIGN,
    "marketing_recommendation_agent": MARKETING_OUTPUT,
    "evaluation_agent":               EVALUATION_OUTPUT,
    "channel_adaptation_agent":       CHANNEL_ADAPTATION,
    "brand_consistency_agent":        BRAND_CONSISTENCY,
}

# Agents whose failure does not stop the rest of the pipeline being surfaced
_NON_CRITICAL_AGENTS = {
    "trend_validator_agent",
    "competitor_agent",
    "pricing_analysis_agent",
    "marketing_recommendation_agent",
    "evaluation_agent",
    "channel_adaptation_agent",
    "campaign_architecture_agent",
    "experiment_design_agent",
    "brand_consistency_agent",
}

# Total tracked agent completions for progress bar (excludes loop_evaluator internal signal)
_TOTAL_AGENTS = 16

# Gemini 2.0 Flash pricing (USD per million tokens, as of 2025)
_INPUT_COST_PER_M = 0.075
_OUTPUT_COST_PER_M = 0.30


def _sse(event: str, data: dict) -> str:
    return f"data: {json.dumps({'event': event, **data})}\n\n"


def _parse_json_output(raw: str | None) -> dict | str:
    if not raw:
        return {}
    text = raw.strip()
    # Strip markdown code fences that LLMs occasionally emit despite instructions
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop opening fence line (```json or ```) and closing ``` if present
        start = 1
        end = len(lines)
        if lines[-1].strip() == "```":
            end -= 1
        text = "\n".join(lines[start:end]).strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("_parse_json_output: could not parse as JSON (len=%d, preview=%r)", len(raw), raw[:200])
        return raw or {}


@router.post("")
async def generate_ad(
    request: GenerationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    async def event_stream() -> AsyncGenerator[str, None]:
        from sqlalchemy import select
        from backend.models.product import Product
        from backend.models.campaign import Campaign

        # 0. Load and validate product BEFORE creating any records
        product = await db.scalar(select(Product).where(Product.id == request.product_id))
        if not product:
            yield _sse("error", {"agent": "pipeline", "data": {"message": "Product not found."}})
            return
        if not (product.description or "").strip():
            yield _sse("error", {"agent": "pipeline", "data": {
                "message": (
                    f"Product '{product.name}' has no description. "
                    "Please add a product description before generating an ad — "
                    "the pipeline agents rely on it to understand what to advertise."
                )
            }})
            return

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

        # Register cancellation flag for this run
        cancel_evt = asyncio.Event()
        _cancellation_flags[ad_id] = cancel_evt

        # Store channel on the ad record
        if request.target_channel:
            ad.target_channel = request.target_channel
            await db.commit()

        yield _sse("started", {"advertisement_id": ad_id})

        # 2. Build product description + marketing brief
        # Use `or ""` to guard against a None description slipping through as
        # the literal string "None" inside the prompt.
        desc_text = (product.description or "").strip()
        product_desc = f"{product.name}\n{desc_text}" if desc_text else product.name
        if product.unit_cost_usd is not None:
            product_desc += f"\nUnit Cost (per unit): ${product.unit_cost_usd:.2f}"

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
            EXTRA_INPUT: "",        # always present so prompts with {extra_input} don't raise KeyError
            LOOP_FEEDBACK: "",      # pre-seeded: missing on iteration 1 of positioning_segmentation_loop
            MARKET_SEGMENTATION: "",   # pre-seeded: used as template var by pricing/campaign/experiment agents
            PRICING_ANALYSIS: "",      # pre-seeded: non-critical agent may be skipped before campaign_architecture runs
            CAMPAIGN_ARCHITECTURE: "", # pre-seeded: non-critical agent may be skipped before experiment_design runs
        }

        # Log all user inputs at pipeline start for observability / debugging
        pl.log_generation_start(
            user_id=str(current_user.id),
            product_id=request.product_id,
            product_name=product.name,
            product_description=desc_text,
            campaign_id=request.campaign_id,
            marketing_brief=marketing_brief,
            target_channel=request.target_channel,
            image_gen_provider=settings.image_gen_provider,
            persona_ids=request.persona_ids,
        )

        # 5. Run ADK pipeline, streaming events
        session_id = f"ad_{ad_id}"
        user_id = current_user.id
        progress = 0
        # Track completed state keys to avoid double-counting loop iterations in progress bar.
        # A loop agent (e.g. positioning_segmentation_loop) fires is_final_response() once per
        # iteration for each sub-agent; only the first completion of each state_key counts.
        completed_state_keys: set[str] = set()
        # Charts captured from execute_python FunctionResponse events, keyed by agent name.
        # Injected into the agent's parsed output after its final response, so agents never
        # need to reproduce large base64 strings in their JSON text output.
        _pending_charts: dict[str, list[str]] = {}

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
                # Track agent start times for telemetry; emit agent_start SSE on first event
                if hasattr(event, "author") and event.author and event.author not in agent_start_times:
                    agent_start_times[event.author] = time.monotonic()
                    if event.author in _AGENT_KEY_MAP:
                        yield _sse("agent_start", {"agent": _AGENT_KEY_MAP[event.author]})

                _evt_author = getattr(event, 'author', '?')
                if _evt_author == 'experiment_design_agent' or logger.isEnabledFor(logging.DEBUG):
                    _dbg_parts = []
                    if event.content and event.content.parts:
                        for _p in event.content.parts:
                            if getattr(_p, 'text', None):
                                _dbg_parts.append(f"text({len(_p.text)}ch)")
                            elif getattr(_p, 'function_call', None):
                                _dbg_parts.append(f"fn_call({_p.function_call.name})")
                            elif getattr(_p, 'function_response', None):
                                _dbg_parts.append(f"fn_resp({_p.function_response.name})")
                            else:
                                _dbg_parts.append("other")
                    _finish = None
                    for _attr in ('finish_reason', 'candidates'):
                        _v = getattr(event, _attr, None)
                        if _v is not None:
                            _finish = f"{_attr}={_v!r:.80}"
                            break
                    logger.info(
                        "adk_event ad=%s author=%s is_final=%s parts=%s delta_keys=%s finish=%s etype=%s",
                        ad_id,
                        _evt_author,
                        event.is_final_response(),
                        _dbg_parts,
                        list((getattr(event.actions, 'state_delta', None) or {}).keys()) if event.actions else [],
                        _finish,
                        type(event).__name__,
                    )

                # Collect base64 charts from execute_python tool responses.
                # Charts are stored in a module-level registry (keyed by UUID) so that
                # the LLM never sees large base64 data. We drain by _charts_id here.
                if event.author and event.content and event.content.parts:
                    for _part in event.content.parts:
                        _fn_resp = getattr(_part, 'function_response', None)
                        if _fn_resp is not None and getattr(_fn_resp, 'name', None) == 'execute_python':
                            _resp = getattr(_fn_resp, 'response', None) or {}
                            if isinstance(_resp, dict):
                                _charts_id = _resp.get('_charts_id')
                                if _charts_id:
                                    from tools.code_tools import drain_charts
                                    for _c in drain_charts(_charts_id):
                                        _pending_charts.setdefault(event.author, []).append(_c)

                # Detect agent completion events
                if event.is_final_response() and event.author in _AGENT_KEY_MAP:
                    agent_name = event.author
                    state_key = _AGENT_KEY_MAP[agent_name]
                    # Only count the first completion of each state key toward progress.
                    # Loop agents (market_segmentation, audience_analysis, loop_eval_signal)
                    # fire once per iteration; the internal loop_eval_signal has no UI tab.
                    is_first_completion = state_key not in completed_state_keys and state_key != LOOP_EVAL_SIGNAL
                    if is_first_completion:
                        progress += 1
                        completed_state_keys.add(state_key)
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

                    # Retrieve the agent's output.
                    # Priority 1 — event.actions.state_delta: for sub-agents inside a LoopAgent,
                    # DatabaseSessionService does not commit state between iterations; state_delta
                    # contains the in-memory writes from this specific event and is always current.
                    # Priority 2 — event.content text: same text that LlmAgent writes to output_key;
                    # present when state_delta doesn't carry the key (ADK version-specific).
                    # Priority 3 — session service: reliable for non-loop sequential agents.
                    raw_output = None
                    try:
                        delta = (getattr(event.actions, "state_delta", None) or {}) if event.actions else {}
                        raw_output = delta.get(state_key)
                    except Exception:
                        pass
                    if raw_output is None and event.content and event.content.parts:
                        text_parts = [p.text for p in event.content.parts if getattr(p, "text", None)]
                        if text_parts:
                            raw_output = text_parts[-1]
                    if raw_output is None:
                        current_session = await runner.session_service.get_session(
                            app_name="ad_synth_ai",
                            user_id=user_id,
                            session_id=session_id,
                        )
                        raw_output = current_session.state.get(state_key, "")
                    # ADK may store state values as native dicts; normalize to string for downstream processing
                    if isinstance(raw_output, dict):
                        raw_output = json.dumps(raw_output)
                    raw_output = raw_output or ""
                    logger.info(
                        "agent_output_raw ad=%s agent=%s key=%s len=%d output=%r",
                        ad_id, agent_name, state_key, len(raw_output or ""), (raw_output or "")[:2000],
                    )
                    parsed = _parse_json_output(raw_output)

                    # Inject base64 charts captured from execute_python tool calls.
                    # Agents set image_base64: null in their JSON; we fill it here so
                    # the model never has to reproduce large binary data as text.
                    _agent_charts = _pending_charts.pop(agent_name, [])
                    if _agent_charts and isinstance(parsed, dict):
                        _existing = parsed.get('charts') or []
                        if not isinstance(_existing, list):
                            _existing = []
                        for _i, _b64 in enumerate(_agent_charts):
                            if _i < len(_existing) and isinstance(_existing[_i], dict):
                                _existing[_i]['image_base64'] = _b64
                            else:
                                _existing.append({
                                    'title': f'Chart {_i + 1}',
                                    'description': 'Generated analysis chart',
                                    'image_base64': _b64,
                                })
                        parsed['charts'] = _existing

                    # Build a lightweight summary for the pipeline log
                    output_summary: dict = {"parsed_keys": list(parsed.keys()) if isinstance(parsed, dict) else []}
                    if isinstance(parsed, dict):
                        if state_key == PRODUCT_PROFILE:
                            output_summary["product_name_literal"] = parsed.get("product_name_literal", "")
                            output_summary["product_type"] = parsed.get("product_type", "")
                        elif state_key == IMAGE_GEN_PROMPT:
                            output_summary["has_image_gen_prompt"] = bool(parsed.get("image_gen_prompt"))
                            output_summary["has_ab_variant_prompt"] = bool(parsed.get("ab_variant_prompt"))
                    pl.log_agent_output(
                        agent_name=agent_name,
                        state_key=state_key,
                        parsed_type=type(parsed).__name__,
                        raw_len=len(raw_output or ""),
                        output_summary=output_summary,
                        output_json_preview=raw_output or "",
                    )

                    # Persist to DB
                    await advertisement_service.update_pipeline_state(ad, state_key, parsed, db)

                    # Special handling: extract specific fields from outputs
                    if state_key == IMAGE_GEN_PROMPT:
                        if isinstance(parsed, dict):
                            prompt_text = parsed.get("image_gen_prompt") or ""
                            if prompt_text:
                                ad.image_gen_prompt = prompt_text
                                logger.info(
                                    "image_gen_prompt_set ad=%s prompt_len=%d preview=%r",
                                    ad_id, len(prompt_text), prompt_text[:150],
                                )
                            else:
                                logger.warning(
                                    "image_gen_prompt_missing ad=%s parsed_keys=%s",
                                    ad_id, list(parsed.keys()),
                                )
                            if parsed.get("ab_variant_prompt"):
                                ad.ab_variant_prompt = parsed["ab_variant_prompt"]
                        else:
                            logger.warning(
                                "image_gen_prompt_not_dict ad=%s parsed_type=%s raw_preview=%r",
                                ad_id, type(parsed).__name__, (raw_output or "")[:300],
                            )
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

                    # New pipeline outputs — persist to pipeline_state (already done above
                    # via update_pipeline_state); no additional ad-model fields needed.

                    if state_key == SELECTED_PERSONA and isinstance(parsed, dict):
                        if parsed.get("save_new_persona") and isinstance(parsed.get("persona"), dict):
                            from backend.models.persona import Persona as PersonaModel
                            p_data = parsed["persona"]
                            traits = {k: v for k, v in p_data.items() if k != "name"}
                            new_persona = PersonaModel(
                                campaign_id=str(request.campaign_id),
                                name=p_data.get("name", "Generated Persona"),
                                traits=json.dumps(traits),
                            )
                            db.add(new_persona)
                            await db.commit()
                            await db.refresh(new_persona)
                            logger.info("Saved new persona %s for campaign %s", new_persona.id, request.campaign_id)

                    yield _sse("agent_complete", {
                        "agent": state_key,
                        "data": parsed,
                        "progress": progress,
                        "total": _TOTAL_AGENTS,
                        "advertisement_id": ad_id,
                    })

                    # Check for cancellation after each agent completes
                    if cancel_evt.is_set():
                        await advertisement_service.set_ad_status(ad, "partial_failure", db)
                        yield _sse("cancelled", {"advertisement_id": ad_id})
                        _cancellation_flags.pop(ad_id, None)
                        return

        except Exception as e:
            logger.exception("Pipeline error for ad %s: %s", ad_id, e)
            await advertisement_service.set_ad_status(ad, "partial_failure", db)
            await advertisement_service.update_pipeline_state(ad, PIPELINE_ERROR, {"message": str(e)}, db)
            yield _sse("error", {"agent": "pipeline", "data": {"message": str(e)}})
        finally:
            _cancellation_flags.pop(ad_id, None)

        # 6a. Pricing fallback — if pricing_analysis_agent was skipped or failed,
        # compute a cost-plus fallback anchored on unit_cost_usd from PRODUCT_PROFILE.
        pricing_state = ad.pipeline_state or {}
        if isinstance(pricing_state, str):
            try:
                pricing_state = json.loads(pricing_state)
            except (json.JSONDecodeError, TypeError):
                pricing_state = {}
        if not pricing_state.get(PRICING_ANALYSIS):
            product_profile_raw = pricing_state.get(PRODUCT_PROFILE, {})
            if isinstance(product_profile_raw, str):
                try:
                    product_profile_raw = json.loads(product_profile_raw)
                except (json.JSONDecodeError, TypeError):
                    product_profile_raw = {}
            if isinstance(product_profile_raw, dict):
                from backend.pipeline.agents.pricing_analysis_agent import compute_pricing_fallback
                fallback = compute_pricing_fallback(product_profile_raw)
                await advertisement_service.update_pipeline_state(ad, PRICING_ANALYSIS, fallback, db)
                logger.info("pricing_fallback_applied ad=%s unit_cost=%s", ad_id, fallback.get("unit_cost_usd"))

        # 6b. Experiment design fallback — if agent failed at high context, inject deterministic fallback.
        if not pricing_state.get(EXPERIMENT_DESIGN):
            from backend.pipeline.agents.experiment_design_agent import compute_experiment_design_fallback
            exp_fallback = compute_experiment_design_fallback()
            await advertisement_service.update_pipeline_state(ad, EXPERIMENT_DESIGN, exp_fallback, db)
            logger.info("experiment_design_fallback_applied ad=%s", ad_id)

        # 6. Trigger image generation
        logger.info(
            "image_gen_check ad=%s has_prompt=%s prompt_len=%s provider=%s",
            ad_id, bool(ad.image_gen_prompt), len(ad.image_gen_prompt or ""), settings.image_gen_provider,
        )
        if ad.image_gen_prompt:
            img_start = time.monotonic()
            try:
                yield _sse("image_generating", {"advertisement_id": ad_id})
                image_provider = create_image_provider()
                logger.info(
                    "image_gen_start ad=%s provider=%s prompt_preview=%r",
                    ad_id, settings.image_gen_provider, ad.image_gen_prompt[:200],
                )
                image_paths = []
                if product and product.image_path:
                    image_paths = [product.image_path]
                generated = await image_provider.generate(ad.image_gen_prompt, image_paths)
                ad.image_url = generated.url
                logger.info("image_gen_success ad=%s url_prefix=%r", ad_id, (generated.url or "")[:80])
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
        raise HTTPException(status_code=404, detail="Advertisement not found")

    campaign = await db.scalar(select(Campaign).where(Campaign.id == ad.campaign_id))
    if not campaign or campaign.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if not ad.ab_variant_prompt and not request.custom_prompt:
        raise HTTPException(status_code=400, detail="No A/B variant prompt available for this advertisement")

    image_provider = create_image_provider()

    if request.custom_prompt:
        # Build composite prompt: prepend original description as context so text-only
        # providers (e.g. ShortAPI) still have enough information to produce a coherent result.
        base_context = f"Original ad description:\n{ad.ab_variant_prompt}\n\n" if ad.ab_variant_prompt else ""
        final_prompt = (
            f"{base_context}"
            f"Modifications to apply: {request.custom_prompt.strip()}\n"
            "Make these changes while keeping all else the same."
        )
        generated = await image_provider.generate(final_prompt, [], reference_image_url=ad.image_url)
    else:
        generated = await image_provider.generate(ad.ab_variant_prompt, [])

    ad.ab_variant_url = generated.url
    await db.commit()

    return {"ab_variant_url": generated.url, "advertisement_id": ad.id}


@router.post("/{ad_id}/retry-image")
async def retry_image_generation(
    ad_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Re-run image generation for an ad whose image failed or is missing."""
    from sqlalchemy import select
    from backend.models.campaign import Campaign

    ad = await db.scalar(select(Advertisement).where(Advertisement.id == ad_id))
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    campaign = await db.scalar(select(Campaign).where(Campaign.id == ad.campaign_id))
    if not campaign or campaign.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not ad.image_gen_prompt:
        raise HTTPException(status_code=400, detail="No image generation prompt available for this ad")

    image_provider = create_image_provider()
    generated = await image_provider.generate(ad.image_gen_prompt, [])
    ad.image_url = generated.url
    await db.commit()
    return {"image_url": generated.url, "advertisement_id": ad.id}


@router.post("/{ad_id}/cancel")
async def cancel_generation(
    ad_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Signal cancellation for an in-progress pipeline run."""
    from sqlalchemy import select
    from backend.models.campaign import Campaign

    ad = await db.scalar(select(Advertisement).where(Advertisement.id == ad_id))
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    campaign = await db.scalar(select(Campaign).where(Campaign.id == ad.campaign_id))
    if not campaign or campaign.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    flag = _cancellation_flags.get(ad_id)
    if flag:
        flag.set()
        return {"status": "cancellation_requested", "advertisement_id": ad_id}
    return {"status": "not_running", "advertisement_id": ad_id}


@router.post("/{ad_id}/rerun-stage")
async def rerun_stage(
    ad_id: str,
    request: RerunStageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Re-run a single pipeline stage (and optionally all downstream stages).

    Snapshots the current output to history, clears downstream state keys,
    optionally injects extra_input into session state, then re-runs the pipeline
    from the target stage forward, streaming SSE events.
    """
    from sqlalchemy import select
    from backend.models.campaign import Campaign
    from backend.models.product import Product

    ad = await db.scalar(select(Advertisement).where(Advertisement.id == ad_id))
    if not ad:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    campaign = await db.scalar(select(Campaign).where(Campaign.id == ad.campaign_id))
    if not campaign or campaign.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    stage_key = request.stage_key
    if stage_key not in DOWNSTREAM_KEYS:
        raise HTTPException(status_code=400, detail=f"Unknown stage key: {stage_key}")

    async def rerun_stream() -> AsyncGenerator[str, None]:
        pipeline_start = time.monotonic()
        agent_telemetry: list[dict] = []

        # Snapshot current state to history before clearing
        await advertisement_service.snapshot_stage_to_history(ad, stage_key, db)

        # Clear downstream keys from pipeline_state
        await advertisement_service.clear_downstream_state(ad, stage_key, DOWNSTREAM_KEYS, db)

        # Load saved session state as starting point for re-run
        existing_state = json.loads(ad.pipeline_state or "{}")

        # Reconstruct original input keys that are NOT stored in pipeline_state
        # (pipeline_state only stores agent outputs, not the user-provided inputs)
        from backend.models.brand_profile import BrandProfile
        product = await db.scalar(select(Product).where(Product.id == ad.product_id))
        if product:
            desc_text = (product.description or "").strip()
            product_desc = f"{product.name}\n{desc_text}" if desc_text else product.name
            existing_state.setdefault(RAW_PRODUCT_DESCRIPTION, product_desc)
        else:
            existing_state.setdefault(RAW_PRODUCT_DESCRIPTION, "")
        existing_state.setdefault(RAW_MARKETING_BRIEF, "")
        existing_state.setdefault(CAMPAIGN_ID, ad.campaign_id)
        existing_state.setdefault(TARGET_CHANNEL, ad.target_channel or "")
        existing_state.setdefault(EXCLUDED_PERSONA_IDS, [])
        existing_state.setdefault(BRAND_PROFILE_CONTEXT, "")
        if ad.brand_profile_id:
            brand = await db.scalar(
                select(BrandProfile).where(BrandProfile.id == ad.brand_profile_id)
            )
            if brand:
                existing_state[BRAND_PROFILE_CONTEXT] = json.dumps({
                    "name": brand.name,
                    "company": brand.company,
                    "mission": brand.mission,
                    "values": brand.values,
                    "brand_guidelines": brand.brand_guidelines,
                    "tone_keywords": brand.tone_keywords,
                })

        # Remove all DOWNSTREAM_KEYS entries from existing_state so they are re-computed
        for k in DOWNSTREAM_KEYS.get(stage_key, []):
            existing_state.pop(k, None)

        # Always ensure extra_input is present; override if caller provided one.
        # Also pre-seed loop and optional-agent state keys so ADK template injection
        # doesn't raise KeyError if the re-run starts at or before the loop.
        existing_state.setdefault(EXTRA_INPUT, "")
        existing_state.setdefault(LOOP_FEEDBACK, "")
        existing_state.setdefault(MARKET_SEGMENTATION, "")
        existing_state.setdefault(PRICING_ANALYSIS, "")
        existing_state.setdefault(CAMPAIGN_ARCHITECTURE, "")
        if request.extra_input:
            existing_state[EXTRA_INPUT] = request.extra_input

        await advertisement_service.set_ad_status(ad, "running", db)
        yield _sse("started", {"advertisement_id": ad_id, "rerun": True, "stage_key": stage_key})

        cancel_evt = asyncio.Event()
        _cancellation_flags[ad_id] = cancel_evt

        try:
            runner = runner_module.get_runner()
            session_id = f"rerun_{ad_id}_{stage_key}_{int(time.monotonic() * 1000)}"
            await runner.session_service.create_session(
                app_name="ad_synth_ai",
                user_id=current_user.id,
                session_id=session_id,
                state=existing_state,
            )

            agent_start_times: dict[str, float] = {}
            progress = 0
            completed_state_keys: set[str] = set()

            async for event in runner.run_async(
                user_id=current_user.id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text="Re-run the pipeline stage and all downstream stages.")],
                ),
            ):
                if hasattr(event, "author") and event.author and event.author not in agent_start_times:
                    agent_start_times[event.author] = time.monotonic()
                    if event.author in _AGENT_KEY_MAP:
                        yield _sse("agent_start", {"agent": _AGENT_KEY_MAP[event.author]})

                if event.is_final_response() and event.author in _AGENT_KEY_MAP:
                    agent_name = event.author
                    state_key = _AGENT_KEY_MAP[agent_name]
                    is_first_completion = state_key not in completed_state_keys and state_key != LOOP_EVAL_SIGNAL
                    if is_first_completion:
                        progress += 1
                        completed_state_keys.add(state_key)
                    end_time = time.monotonic()
                    start_time = agent_start_times.get(agent_name, end_time)

                    input_tokens = output_tokens = 0
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

                    raw_output = None
                    try:
                        delta = (getattr(event.actions, "state_delta", None) or {}) if event.actions else {}
                        raw_output = delta.get(state_key)
                    except Exception:
                        pass
                    if raw_output is None and event.content and event.content.parts:
                        text_parts = [p.text for p in event.content.parts if getattr(p, "text", None)]
                        if text_parts:
                            raw_output = text_parts[-1]
                    if raw_output is None:
                        current_session = await runner.session_service.get_session(
                            app_name="ad_synth_ai",
                            user_id=current_user.id,
                            session_id=session_id,
                        )
                        raw_output = current_session.state.get(state_key, "")
                    if isinstance(raw_output, dict):
                        raw_output = json.dumps(raw_output)
                    raw_output = raw_output or ""
                    parsed = _parse_json_output(raw_output)

                    # Snapshot previous value to history before overwriting
                    await advertisement_service.snapshot_stage_to_history(ad, state_key, db)
                    await advertisement_service.update_pipeline_state(ad, state_key, parsed, db)

                    # Persist dedicated columns
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
                        "total": len(DOWNSTREAM_KEYS.get(request.stage_key, [])),
                        "advertisement_id": ad_id,
                    })

                    if cancel_evt.is_set():
                        await advertisement_service.set_ad_status(ad, "partial_failure", db)
                        yield _sse("cancelled", {"advertisement_id": ad_id})
                        _cancellation_flags.pop(ad_id, None)
                        return

        except Exception as e:
            logger.exception("Re-run error for ad %s stage %s: %s", ad_id, stage_key, e)
            await advertisement_service.set_ad_status(ad, "partial_failure", db)
            yield _sse("error", {"agent": "pipeline", "data": {"message": str(e)}})
        finally:
            _cancellation_flags.pop(ad_id, None)

        # Trigger image re-generation if image_gen_prompt was affected
        if IMAGE_GEN_PROMPT in DOWNSTREAM_KEYS.get(request.stage_key, []) and ad.image_gen_prompt:
            try:
                yield _sse("image_generating", {"advertisement_id": ad_id})
                product = await db.scalar(select(Product).where(Product.id == ad.product_id))
                image_paths = [product.image_path] if product and product.image_path else []
                image_provider = create_image_provider()
                generated = await image_provider.generate(ad.image_gen_prompt, image_paths)
                ad.image_url = generated.url
                if ad.ab_variant_prompt:
                    ab_gen = await image_provider.generate(ad.ab_variant_prompt, image_paths)
                    ad.ab_variant_url = ab_gen.url
                await db.commit()
                yield _sse("image_ready", {
                    "data": {"url": generated.url, "variant_url": ad.ab_variant_url},
                    "advertisement_id": ad_id,
                })
            except Exception as e:
                logger.exception("Re-run image generation failed for ad %s: %s", ad_id, e)
                yield _sse("error", {"agent": "image_generation", "data": {"message": str(e)}})

        total_cost = sum(t["cost_usd"] for t in agent_telemetry)
        total_latency = round((time.monotonic() - pipeline_start) * 1000, 1)
        final_status = "completed" if ad.status != "partial_failure" else "partial_failure"
        await advertisement_service.set_ad_status(ad, final_status, db)
        yield _sse("done", {"advertisement_id": ad_id, "status": final_status, "rerun": True})
        yield _sse("cost_summary", {
            "total_cost_usd": round(total_cost, 6),
            "total_latency_ms": total_latency,
            "per_agent": agent_telemetry,
        })

    return StreamingResponse(rerun_stream(), media_type="text/event-stream")
