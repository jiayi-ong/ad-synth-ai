from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

from backend.core.config import settings
from backend.pipeline.orchestrator import build_pipeline

_runner: Runner | None = None


def get_runner() -> Runner:
    """Returns the singleton ADK Runner, creating it on first call."""
    global _runner
    if _runner is None:
        _runner = _build_runner()
    return _runner


def _build_runner() -> Runner:
    session_service = DatabaseSessionService(db_url=settings.adk_database_url)
    artifact_service = InMemoryArtifactService()
    pipeline = build_pipeline()
    return Runner(
        agent=pipeline,
        app_name="ad_synth_ai",
        session_service=session_service,
        artifact_service=artifact_service,
    )
