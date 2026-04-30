from google.adk.agents import ParallelAgent, SequentialAgent

from backend.pipeline.agents.trend_agents.aggregator_agent import trend_aggregator_agent
from backend.pipeline.agents.trend_agents.critic_agent import trend_critic_agent
from backend.pipeline.agents.trend_agents.keyword_agent import trend_keyword_agent
from backend.pipeline.agents.trend_agents.platform_agents import (
    data_collection_parallel,
)
from backend.pipeline.agents.trend_agents.synthesis_agent import trend_synthesis_agent

# Re-export ParallelAgent for type transparency (not required, but aids inspection)
__all__ = ["trend_agent"]

trend_agent = SequentialAgent(
    name="trend_research_agent",
    description=(
        "Multi-platform trend research sub-pipeline: "
        "keyword extraction → parallel data collection (7 platforms) → "
        "aggregation → product-contextualized synthesis → critique"
    ),
    sub_agents=[
        trend_keyword_agent,
        data_collection_parallel,
        trend_aggregator_agent,
        trend_synthesis_agent,
        trend_critic_agent,
    ],
)
