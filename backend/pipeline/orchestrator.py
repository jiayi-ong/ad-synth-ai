from google.adk.agents import SequentialAgent

from backend.pipeline.agents.audience_agent import audience_agent
from backend.pipeline.agents.creative_agent import creative_agent
from backend.pipeline.agents.marketing_agent import marketing_agent
from backend.pipeline.agents.persona_agent import persona_agent
from backend.pipeline.agents.product_agent import product_agent
from backend.pipeline.agents.prompt_agent import prompt_agent
from backend.pipeline.agents.trend_agent import trend_agent


def build_pipeline() -> SequentialAgent:
    return SequentialAgent(
        name="ad_synthesis_pipeline",
        description="7-agent sequential pipeline: product → audience → trends → creative → persona → prompt → marketing",
        sub_agents=[
            product_agent,
            audience_agent,
            trend_agent,
            creative_agent,
            persona_agent,
            prompt_agent,
            marketing_agent,
        ],
    )
