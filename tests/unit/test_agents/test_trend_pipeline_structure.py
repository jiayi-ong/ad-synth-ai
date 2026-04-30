"""Verify the trend research sub-pipeline is wired correctly."""
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent


def test_trend_agent_is_sequential():
    from backend.pipeline.agents.trend_agent import trend_agent
    assert isinstance(trend_agent, SequentialAgent)


def test_trend_agent_name_unchanged():
    from backend.pipeline.agents.trend_agent import trend_agent
    assert trend_agent.name == "trend_research_agent"


def test_trend_sub_pipeline_has_five_steps():
    from backend.pipeline.agents.trend_agent import trend_agent
    assert len(trend_agent.sub_agents) == 5


def test_data_collection_is_parallel():
    from backend.pipeline.agents.trend_agents.platform_agents import data_collection_parallel
    assert isinstance(data_collection_parallel, ParallelAgent)


def test_data_collection_has_seven_agents():
    from backend.pipeline.agents.trend_agents.platform_agents import data_collection_parallel
    assert len(data_collection_parallel.sub_agents) == 7


def test_trend_critic_writes_trend_research():
    from backend.pipeline.agents.trend_agents.critic_agent import trend_critic_agent
    from backend.pipeline.state_keys import TREND_RESEARCH
    assert trend_critic_agent.output_key == TREND_RESEARCH


def test_trend_keyword_writes_trend_keywords():
    from backend.pipeline.agents.trend_agents.keyword_agent import trend_keyword_agent
    from backend.pipeline.state_keys import TREND_KEYWORDS
    assert trend_keyword_agent.output_key == TREND_KEYWORDS
