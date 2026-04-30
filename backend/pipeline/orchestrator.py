from google.adk.agents import ParallelAgent, SequentialAgent

from backend.pipeline.agents.audience_agent import audience_agent
from backend.pipeline.agents.brand_consistency_agent import brand_consistency_agent
from backend.pipeline.agents.channel_agent import channel_agent
from backend.pipeline.agents.competitor_agent import competitor_agent
from backend.pipeline.agents.creative_agent import creative_agent
from backend.pipeline.agents.evaluation_agent import evaluation_agent
from backend.pipeline.agents.marketing_agent import marketing_agent
from backend.pipeline.agents.persona_agent import persona_agent
from backend.pipeline.agents.product_agent import product_agent
from backend.pipeline.agents.prompt_agent import prompt_agent
from backend.pipeline.agents.trend_pipeline import trend_research_pipeline


def build_pipeline() -> SequentialAgent:
    # Stage 3: Trend research + Competitor analysis run in parallel
    # (both only need PRODUCT_PROFILE + AUDIENCE_ANALYSIS)
    research_parallel = ParallelAgent(
        name="research_parallel",
        sub_agents=[trend_research_pipeline, competitor_agent],
    )

    # Stage 7: Marketing, Evaluation, and Channel Adaptation run in parallel
    # (all synthesize final state; none depend on each other)
    synthesis_parallel = ParallelAgent(
        name="synthesis_parallel",
        sub_agents=[marketing_agent, evaluation_agent, channel_agent],
    )

    return SequentialAgent(
        name="ad_synthesis_pipeline",
        description=(
            "11-agent pipeline: product → audience → [trend+competitor] → "
            "creative → persona → prompt → [marketing+evaluation+channel] → brand_check"
        ),
        sub_agents=[
            product_agent,        # 1 — extracts product attributes
            audience_agent,       # 2 — audience + positioning (needs product)
            research_parallel,    # 3 — trend pipeline + competitor (parallel, need product+audience)
            creative_agent,       # 4 — creative directions (needs trend+competitor)
            persona_agent,        # 5 — persona selection (needs creative)
            prompt_agent,         # 6 — image-gen prompt (needs all above)
            synthesis_parallel,   # 7 — marketing + evaluation + channel (parallel synthesis)
            brand_consistency_agent,  # 8 — brand check (needs marketing output)
        ],
    )
