from google.adk.agents import ParallelAgent, SequentialAgent

from backend.pipeline.agents.reddit_search_agent import reddit_search_agent
from backend.pipeline.agents.trend_query_agent import trend_query_agent
from backend.pipeline.agents.trend_synthesis_agent import trend_synthesis_agent
from backend.pipeline.agents.web_search_agent import web_search_agent

# Parallel web + Reddit search after queries are formulated
_search_parallel = ParallelAgent(
    name="search_parallel",
    sub_agents=[web_search_agent, reddit_search_agent],
)

# Full trend research pipeline: formulate queries → parallel search → synthesize
trend_research_pipeline = SequentialAgent(
    name="trend_research_pipeline",
    description="3-stage trend research: query formulation → parallel web+Reddit search → synthesis",
    sub_agents=[
        trend_query_agent,
        _search_parallel,
        trend_synthesis_agent,
    ],
)
