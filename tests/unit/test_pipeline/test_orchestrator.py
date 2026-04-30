"""Unit tests for the pipeline orchestrator structure.

ADK agents are module-level singletons — they can only have one parent.
We access the pipeline via the runner singleton (get_runner().agent) so that
whether the runner was already initialized by other tests or not, we always
get the same pipeline object with no re-parenting attempt.
"""
import pytest
from google.adk.agents import ParallelAgent, SequentialAgent


@pytest.fixture(scope="session")
def pipeline():
    """Returns the built pipeline, reusing the runner singleton if already initialized."""
    from backend.pipeline.runner import get_runner
    return get_runner().agent


@pytest.mark.unit
def test_build_pipeline_returns_sequential_agent(pipeline):
    assert isinstance(pipeline, SequentialAgent)


@pytest.mark.unit
def test_pipeline_name(pipeline):
    assert pipeline.name == "ad_synthesis_pipeline"


@pytest.mark.unit
def test_pipeline_has_eight_top_level_sub_agents(pipeline):
    assert len(pipeline.sub_agents) == 8


@pytest.mark.unit
def test_research_parallel_is_second_stage(pipeline):
    research_stage = pipeline.sub_agents[2]
    assert isinstance(research_stage, ParallelAgent)
    assert research_stage.name == "research_parallel"


@pytest.mark.unit
def test_research_parallel_contains_trend_and_competitor(pipeline):
    research_parallel = pipeline.sub_agents[2]
    sub_names = [a.name for a in research_parallel.sub_agents]
    assert "competitor_agent" in sub_names
    assert any("trend" in name for name in sub_names)


@pytest.mark.unit
def test_synthesis_parallel_is_seventh_stage(pipeline):
    synthesis_stage = pipeline.sub_agents[6]
    assert isinstance(synthesis_stage, ParallelAgent)
    assert synthesis_stage.name == "synthesis_parallel"


@pytest.mark.unit
def test_synthesis_parallel_contains_three_agents(pipeline):
    synthesis_parallel = pipeline.sub_agents[6]
    assert len(synthesis_parallel.sub_agents) == 3


@pytest.mark.unit
def test_synthesis_parallel_agent_names(pipeline):
    synthesis_parallel = pipeline.sub_agents[6]
    sub_names = [a.name for a in synthesis_parallel.sub_agents]
    assert "marketing_recommendation_agent" in sub_names
    assert "evaluation_agent" in sub_names
    assert "channel_adaptation_agent" in sub_names


@pytest.mark.unit
def test_brand_consistency_is_last_stage(pipeline):
    last = pipeline.sub_agents[-1]
    assert last.name == "brand_consistency_agent"
