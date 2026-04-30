"""Connection test: Google Cloud Vertex AI (Application Default Credentials)."""
import os

import pytest

pytestmark = pytest.mark.connection

USE_VERTEXAI = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").upper()
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")


@pytest.fixture(autouse=True)
def skip_if_not_configured():
    if USE_VERTEXAI != "TRUE":
        pytest.skip("GOOGLE_GENAI_USE_VERTEXAI is not TRUE")
    if not GCP_PROJECT_ID:
        pytest.skip("GCP_PROJECT_ID not set")


def test_application_default_credentials_available():
    """Verifies ADC is configured and a token can be obtained."""
    try:
        import google.auth
        credentials, project = google.auth.default()
        assert credentials is not None, "No default credentials found"
        print(f"\n  ADC project: {project or GCP_PROJECT_ID}")
        print("  Status: ADC CONFIGURED ✓")
    except Exception as e:
        pytest.fail(
            f"Application Default Credentials not available: {e}\n"
            "Run: gcloud auth application-default login"
        )


def test_vertex_ai_gemini_responds():
    """Makes a minimal Vertex AI Gemini call to verify project access."""
    from google import genai
    from backend.core.config import settings

    try:
        client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_region,
        )
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents="Reply with exactly: VERTEX_CONNECTED",
        )
        assert response is not None
        text = response.text or ""
        assert len(text) > 0, "Vertex AI returned empty response"
        print(f"\n  Vertex AI response: '{text.strip()}'")
        print(f"  Project: {settings.gcp_project_id}")
        print(f"  Region: {settings.gcp_region}")
        print("  Status: VERTEX AI CONNECTED ✓")
    except Exception as e:
        pytest.fail(
            f"Vertex AI connection failed: {e}\n"
            "Check: GCP_PROJECT_ID, GCP_REGION, Vertex AI API enabled, ADC credentials"
        )


def test_vertex_ai_project_id_is_set():
    from backend.core.config import settings
    assert settings.gcp_project_id, (
        "GCP_PROJECT_ID is empty. Set it in .env:\n"
        "  GCP_PROJECT_ID=your-project-id"
    )
    print(f"\n  GCP_PROJECT_ID: {settings.gcp_project_id} ✓")
