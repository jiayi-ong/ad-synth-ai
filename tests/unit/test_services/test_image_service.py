"""Tests for the multi-provider image generation service."""
from unittest.mock import AsyncMock, MagicMock, patch


def test_factory_returns_mock_by_default(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "image_gen_provider", "mock")
    from backend.services.image_service import MockImageGenProvider, create_image_provider
    assert isinstance(create_image_provider(), MockImageGenProvider)


def test_factory_returns_vertexai(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "image_gen_provider", "vertexai")
    from backend.services.image_service import VertexAIImagenProvider, create_image_provider
    assert isinstance(create_image_provider(), VertexAIImagenProvider)


def test_factory_returns_gemini(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "image_gen_provider", "gemini")
    from backend.services.image_service import GeminiImageProvider, create_image_provider
    assert isinstance(create_image_provider(), GeminiImageProvider)


def test_factory_returns_shortapi(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "image_gen_provider", "shortapi")
    from backend.services.image_service import ShortAPIProvider, create_image_provider
    assert isinstance(create_image_provider(), ShortAPIProvider)


def test_mock_provider_returns_placeholder():
    import asyncio
    from backend.services.image_service import MockImageGenProvider
    result = asyncio.run(MockImageGenProvider().generate("test prompt", []))
    assert "placehold.co" in result.url


def test_shortapi_raises_without_key(monkeypatch):
    import asyncio
    from backend.core.config import settings
    monkeypatch.setattr(settings, "shortapi_api_key", "")
    from backend.services.image_service import ShortAPIProvider
    import pytest
    with pytest.raises(RuntimeError, match="SHORTAPI_API_KEY"):
        asyncio.run(ShortAPIProvider().generate("test", []))


def test_gemini_provider_extracts_image_part(monkeypatch):
    import asyncio, base64
    from backend.core.config import settings
    monkeypatch.setattr(settings, "google_genai_use_vertexai", False)
    monkeypatch.setattr(settings, "google_api_key", "fake-key")
    monkeypatch.setattr(settings, "gemini_image_model", "gemini-test-image-model")

    fake_bytes = b"\x89PNG\r\n"
    mock_part = MagicMock()
    mock_part.inline_data = MagicMock()
    mock_part.inline_data.data = fake_bytes
    mock_part.inline_data.mime_type = "image/png"

    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]
    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        from backend.services.image_service import GeminiImageProvider
        result = asyncio.run(GeminiImageProvider().generate("test prompt", []))

    expected_b64 = base64.b64encode(fake_bytes).decode()
    assert result.base64 == expected_b64
    assert result.url.startswith("data:image/png;base64,")
