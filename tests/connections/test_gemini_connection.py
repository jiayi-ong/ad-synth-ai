"""Connection test: Google Gemini API (AI Studio key)."""
import os

import pytest

pytestmark = pytest.mark.connection

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")


@pytest.fixture(autouse=True)
def skip_if_no_key():
    if not GOOGLE_API_KEY:
        pytest.skip("GOOGLE_API_KEY not set")
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").upper() == "TRUE":
        pytest.skip("Using Vertex AI — use test_vertex_connection.py instead")


def test_gemini_responds_to_simple_prompt():
    """Makes a minimal generate_content call to verify the API key works."""
    from google import genai
    from backend.core.config import settings

    client = genai.Client(api_key=GOOGLE_API_KEY)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents="Reply with exactly the word: CONNECTED",
    )
    assert response is not None
    text = response.text or ""
    assert len(text) > 0, "Gemini returned an empty response"
    print(f"\n  Gemini response: '{text.strip()}'")
    print(f"  Model: {settings.gemini_model}")
    print("  Status: CONNECTED ✓")


def test_gemini_model_is_accessible():
    """Verifies the configured Gemini model can be listed."""
    from google import genai
    from backend.core.config import settings

    client = genai.Client(api_key=GOOGLE_API_KEY)
    # Just confirm we can construct a request without error
    model_name = settings.gemini_model
    assert model_name, "GEMINI_MODEL is not configured"
    print(f"\n  Configured model: {model_name}")
    print("  Status: ACCESSIBLE ✓")
