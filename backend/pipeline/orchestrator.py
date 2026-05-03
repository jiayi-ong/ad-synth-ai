from google.adk.agents import ParallelAgent, SequentialAgent

from backend.pipeline.agents.brand_consistency_agent import brand_consistency_agent
from backend.pipeline.agents.campaign_architecture_agent import campaign_architecture_agent
from backend.pipeline.agents.channel_agent import channel_agent
from backend.pipeline.agents.competitor_agent import competitor_agent
from backend.pipeline.agents.creative_agent import creative_agent
from backend.pipeline.agents.evaluation_agent import evaluation_agent
from backend.pipeline.agents.experiment_design_agent import experiment_design_agent
from backend.pipeline.agents.marketing_agent import marketing_agent
from backend.pipeline.agents.persona_agent import persona_agent
from backend.pipeline.agents.positioning_segmentation_loop import positioning_segmentation_loop
from backend.pipeline.agents.pricing_analysis_agent import pricing_analysis_agent
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

    # Stage 10: Marketing, Evaluation, and Channel Adaptation run in parallel
    # (all synthesize final state; none depend on each other)
    synthesis_parallel = ParallelAgent(
        name="synthesis_parallel",
        sub_agents=[marketing_agent, evaluation_agent, channel_agent],
    )

    return SequentialAgent(
        name="ad_synthesis_pipeline",
        description=(
            "16-agent pipeline: product → [segmentation↔positioning loop] → "
            "[trend+competitor] → pricing → creative → persona → prompt → "
            "campaign_architecture → experiment_design → "
            "[marketing+evaluation+channel] → brand_check"
        ),
        sub_agents=[
            product_agent,                   # 1 — product analysis + compliance flags
            positioning_segmentation_loop,   # 2 — LoopAgent: segmentation ↔ positioning (max 3 iterations)
            research_parallel,               # 3 — trend pipeline + competitor (parallel)
            pricing_analysis_agent,          # 4 — financial modeling (needs competitor pricing)
            creative_agent,                  # 5 — creative directions (needs trend+competitor+pricing)
            persona_agent,                   # 6 — persona selection
            prompt_agent,                    # 7 — image-gen prompt
            campaign_architecture_agent,     # 8 — campaign blueprint
            experiment_design_agent,         # 9 — A/B test plan with scipy power analysis
            synthesis_parallel,              # 10 — marketing + evaluation + channel (parallel)
            brand_consistency_agent,         # 11 — brand check
        ],
    )
