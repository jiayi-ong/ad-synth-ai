from google.adk.agents import ParallelAgent, SequentialAgent

from backend.pipeline.agents.trend_agents.aggregator_agent import trend_aggregator_agent
from backend.pipeline.agents.trend_agents.keyword_agent import trend_keyword_agent
from backend.pipeline.agents.trend_agents.platform_agents import data_collection_parallel
from backend.pipeline.agents.trend_agents.quantitative_agent import build_quantitative_analysis_agent
from backend.pipeline.agents.trend_agents.sentiment_agent import build_sentiment_analysis_agent
from backend.pipeline.agents.trend_agents.synthesis_agent import trend_synthesis_agent
from backend.pipeline.agents.trend_agents.validator_agent import build_trend_validator_agent

__all__ = ["trend_agent"]

trend_agent = SequentialAgent(
    name="trend_research_agent",
    description=(
        "Multi-platform trend research sub-pipeline: "
        "keyword extraction → parallel data collection (7 platforms) → "
        "aggregation → quantitative analysis → sentiment analysis → "
        "synthesis → validation"
    ),
    sub_agents=[
        trend_keyword_agent,
        data_collection_parallel,
        trend_aggregator_agent,
        build_quantitative_analysis_agent(),
        build_sentiment_analysis_agent(),
        trend_synthesis_agent,
        build_trend_validator_agent(),
    ],
)
