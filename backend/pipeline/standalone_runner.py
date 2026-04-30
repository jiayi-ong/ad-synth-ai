"""Lightweight ADK runners for single-agent or small sub-pipeline execution."""
import uuid

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


def build_single_agent_runner(agent: LlmAgent) -> Runner:
    """Build an ephemeral Runner wrapping a single agent (uses in-memory sessions)."""
    pipeline = SequentialAgent(name=f"{agent.name}_pipeline", sub_agents=[agent])
    return Runner(
        agent=pipeline,
        app_name="ad_synth_ai_standalone",
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
    )


def build_pipeline_runner(pipeline: SequentialAgent) -> Runner:
    """Build an ephemeral Runner wrapping an arbitrary pipeline."""
    return Runner(
        agent=pipeline,
        app_name="ad_synth_ai_standalone",
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
    )


async def run_agent_with_state(agent: LlmAgent, state: dict, user_id: str = "standalone") -> dict:
    """
    Run a single agent with a pre-populated state dict and return the final session state.
    Useful for synchronous-style evaluation calls.
    """
    runner = build_single_agent_runner(agent)
    session_id = f"standalone_{uuid.uuid4().hex[:8]}"
    await runner.session_service.create_session(
        app_name="ad_synth_ai_standalone",
        user_id=user_id,
        session_id=session_id,
        state=state,
    )
    async for _ in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="Perform your analysis based on the session state provided.")],
        ),
    ):
        pass  # Drain the stream; state is updated as side-effect

    session = await runner.session_service.get_session(
        app_name="ad_synth_ai_standalone",
        user_id=user_id,
        session_id=session_id,
    )
    return dict(session.state)
