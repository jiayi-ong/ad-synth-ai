from google.adk.agents import ParallelAgent, SequentialAgent

from backend.pipeline.agents.reddit_search_agent import build_reddit_search_agent, reddit_search_agent
from backend.pipeline.agents.trend_query_agent import build_trend_query_agent, trend_query_agent
from backend.pipeline.agents.trend_synthesis_agent import build_trend_synthesis_agent, trend_synthesis_agent
from backend.pipeline.agents.web_search_agent import build_web_search_agent, web_search_agent
from backend.pipeline.agents.trend_agents.quantitative_agent import (
    build_quantitative_analysis_agent,
    quantitative_analysis_agent,
)
from backend.pipeline.agents.trend_agents.sentiment_agent import (
    build_sentiment_analysis_agent,
    sentiment_analysis_agent,
)
from backend.pipeline.agents.trend_agents.validator_agent import (
    build_trend_validator_agent,
    trend_validator_agent,
)

# Parallel web + Reddit search after queries are formulated
_search_parallel = ParallelAgent(
    name="search_parallel",
    sub_agents=[web_search_agent, reddit_search_agent],
)

# Full standalone pipeline:
# query formulation → parallel web+Reddit search
# → quantitative analysis → sentiment analysis → synthesis → validation
trend_research_pipeline = SequentialAgent(
    name="trend_research_pipeline",
    description=(
        "6-stage trend research: query formulation → parallel web+Reddit search → "
        "quantitative analysis → sentiment analysis → synthesis → validation"
    ),
    sub_agents=[
        trend_query_agent,
        _search_parallel,
        quantitative_analysis_agent,
        sentiment_analysis_agent,
        trend_synthesis_agent,
        trend_validator_agent,
    ],
)


def build_trend_research_pipeline() -> SequentialAgent:
    """Build a fresh (unparented) trend research pipeline for standalone use."""
    search_parallel = ParallelAgent(
        name="search_parallel",
        sub_agents=[build_web_search_agent(), build_reddit_search_agent()],
    )
    return SequentialAgent(
        name="trend_research_pipeline",
        description=(
            "6-stage trend research: query formulation → parallel web+Reddit search → "
            "quantitative analysis → sentiment analysis → synthesis → validation"
        ),
        sub_agents=[
            build_trend_query_agent(),
            search_parallel,
            build_quantitative_analysis_agent(),
            build_sentiment_analysis_agent(),
            build_trend_synthesis_agent(),
            build_trend_validator_agent(),
        ],
    )
