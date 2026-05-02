import json
import logging
import uuid
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from google.adk.agents import ParallelAgent
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import get_current_user
from backend.db.session import get_db
from backend.models.user import User
from backend.pipeline.agents.competitor_agent import build_competitor_agent
from backend.pipeline.agents.trend_pipeline import build_trend_research_pipeline
from backend.pipeline.standalone_runner import build_pipeline_runner
from backend.pipeline.state_keys import (
    COMPETITOR_ANALYSIS,
    QUANTITATIVE_INSIGHTS,
    RAW_MARKETING_BRIEF,
    RAW_PRODUCT_DESCRIPTION,
    SENTIMENT_INSIGHTS,
    TREND_RESEARCH,
)
from backend.schemas.research import ResearchRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/research", tags=["research"])


def _sse(event: str, data: dict) -> str:
    return f"data: {json.dumps({'event': event, **data})}\n\n"


@router.post("")
async def run_research(
    request: ResearchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Standalone trend and competitor research pipeline.
    Streams SSE events as each agent completes.
    Results are stored in research_cache for future retrieval.
    """
    async def event_stream() -> AsyncGenerator[str, None]:
        research_id = str(uuid.uuid4())
        yield _sse("started", {"research_id": research_id})

        # Build initial state
        audience_note = f"Target audience: {request.target_audience}" if request.target_audience else ""
        initial_state = {
            RAW_PRODUCT_DESCRIPTION: request.product_description,
            RAW_MARKETING_BRIEF: audience_note,
            "product_profile": json.dumps({
                "overall_summary": request.product_description,
                "product_type": request.product_description.split()[0] if request.product_description else "",
            }),
            "audience_analysis": json.dumps({
                "overall_summary": audience_note or request.product_description,
                "primary_audience": {"demographics": audience_note},
            }),
            "force_refresh": request.force_refresh,
        }

        try:
            from google.adk.agents import SequentialAgent
            # Build fresh (unparented) agent instances — the module-level singletons
            # are already parented to the main ad-generation pipeline.
            if request.research_type == "trends":
                pipeline = build_trend_research_pipeline()
            elif request.research_type == "competitors":
                pipeline = build_competitor_agent()
                pipeline = SequentialAgent(name="research_wrapper", sub_agents=[pipeline])
            else:
                parallel = ParallelAgent(
                    name="research_pipeline",
                    sub_agents=[build_trend_research_pipeline(), build_competitor_agent()],
                )
                pipeline = SequentialAgent(name="research_wrapper", sub_agents=[parallel])

            runner = build_pipeline_runner(
                pipeline if isinstance(pipeline, SequentialAgent) else
                SequentialAgent(name="research_wrapper", sub_agents=[pipeline])
            )

            session_id = f"research_{research_id}"
            user_id = current_user.id
            await runner.session_service.create_session(
                app_name="ad_synth_ai_standalone",
                user_id=user_id,
                session_id=session_id,
                state=initial_state,
            )

            _key_map = {
                "quantitative_analysis_agent": QUANTITATIVE_INSIGHTS,
                "sentiment_analysis_agent": SENTIMENT_INSIGHTS,
                "trend_validator_agent": TREND_RESEARCH,
                "competitor_agent": COMPETITOR_ANALYSIS,
                # Legacy: emit event if old synthesis agent fires (no validator yet)
                "trend_synthesis_agent": TREND_RESEARCH,
            }

            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[types.Part(text="Research trends and competitor intelligence based on the product description in session state.")],
                ),
            ):
                if event.is_final_response() and hasattr(event, "author") and event.author in _key_map:
                    state_key = _key_map[event.author]
                    current_session = await runner.session_service.get_session(
                        app_name="ad_synth_ai_standalone",
                        user_id=user_id,
                        session_id=session_id,
                    )
                    raw = current_session.state.get(state_key, "")
                    try:
                        parsed = json.loads(raw) if isinstance(raw, str) else raw
                    except (json.JSONDecodeError, TypeError):
                        parsed = raw or {}
                    yield _sse("agent_complete", {"agent": state_key, "data": parsed, "research_id": research_id})

            # Retrieve final state and store results
            final_session = await runner.session_service.get_session(
                app_name="ad_synth_ai_standalone", user_id=user_id, session_id=session_id,
            )
            trend_result = final_session.state.get(TREND_RESEARCH)
            competitor_result = final_session.state.get(COMPETITOR_ANALYSIS)

            # Persist to research cache DB
            try:
                from tools.research_cache_tools import store_research_cache
                combined = json.dumps({
                    "trends": trend_result,
                    "competitors": competitor_result,
                    "research_id": research_id,
                })
                store_research_cache(request.product_description, combined, query_type=request.research_type)
            except Exception as cache_err:
                logger.warning("Failed to persist research cache: %s", cache_err)

            yield _sse("done", {
                "research_id": research_id,
                "status": "completed",
                "trend_result": trend_result,
                "competitor_result": competitor_result,
            })

        except Exception as e:
            logger.exception("Research pipeline failed: %s", e)
            yield _sse("error", {"data": {"message": str(e)}, "research_id": research_id})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
