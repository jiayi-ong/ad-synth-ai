"""Tests for the multi-provider image generation service."""
import asyncio
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


# ── ShortAPI HTTP behaviour ────────────────────────────────────────────────────

def _make_shortapi_provider(monkeypatch, api_key: str = "test-key"):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "shortapi_api_key", api_key)
    monkeypatch.setattr(settings, "shortapi_model", "google/nano-banana-pro/text-to-image")
    monkeypatch.setattr(settings, "shortapi_aspect_ratio", "4:5")
    from backend.services.image_service import ShortAPIProvider
    return ShortAPIProvider()


def _mock_httpx_response(json_body: dict, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_body
    mock_resp.is_success = status_code < 400
    mock_resp.text = ""
    if status_code >= 400:
        import httpx
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}", request=MagicMock(), response=MagicMock()
        )
    else:
        mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _make_mock_client(post_response, get_responses=None):
    """Return a mock AsyncClient with configured post/get responses."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=post_response)
    if get_responses is not None:
        mock_client.get = AsyncMock(side_effect=get_responses)
    return mock_client


_CREATE_OK = {"code": 0, "data": {"job_id": "test-job-123"}}
_POLL_DONE = {"code": 0, "data": {"status": 2, "result": {"images": [{"url": "https://cdn.shortapi.ai/img.png"}]}}}
_POLL_PENDING = {"code": 0, "data": {"status": 1}}


def test_shortapi_success_immediate(monkeypatch):
    """Job completes on the first poll."""
    provider = _make_shortapi_provider(monkeypatch)
    mock_client = _make_mock_client(
        post_response=_mock_httpx_response(_CREATE_OK),
        get_responses=[_mock_httpx_response(_POLL_DONE)],
    )
    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        result = asyncio.run(provider.generate("test prompt", []))
    assert result.url == "https://cdn.shortapi.ai/img.png"


def test_shortapi_success_after_polling(monkeypatch):
    """Job is pending on first poll, complete on second."""
    provider = _make_shortapi_provider(monkeypatch)
    mock_client = _make_mock_client(
        post_response=_mock_httpx_response(_CREATE_OK),
        get_responses=[
            _mock_httpx_response(_POLL_PENDING),
            _mock_httpx_response(_POLL_DONE),
        ],
    )
    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        result = asyncio.run(provider.generate("test prompt", []))
    assert result.url == "https://cdn.shortapi.ai/img.png"
    assert mock_client.get.call_count == 2


def test_shortapi_raises_on_http_error(monkeypatch):
    """HTTP error on the create call propagates."""
    import pytest, httpx
    provider = _make_shortapi_provider(monkeypatch)
    mock_client = _make_mock_client(post_response=_mock_httpx_response({}, status_code=429))
    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(provider.generate("test prompt", []))


def test_shortapi_raises_on_api_error(monkeypatch):
    """Non-zero code in create response raises RuntimeError."""
    import pytest
    provider = _make_shortapi_provider(monkeypatch)
    error_resp = {"code": 1, "message": "quota exceeded"}
    mock_client = _make_mock_client(post_response=_mock_httpx_response(error_resp))
    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        with pytest.raises(RuntimeError, match="job create failed"):
            asyncio.run(provider.generate("test prompt", []))


def test_shortapi_raises_on_job_failure(monkeypatch):
    """Terminal failure status in poll raises RuntimeError."""
    import pytest
    provider = _make_shortapi_provider(monkeypatch)
    failed_poll = {"code": 0, "data": {"status": 3}}
    mock_client = _make_mock_client(
        post_response=_mock_httpx_response(_CREATE_OK),
        get_responses=[_mock_httpx_response(failed_poll)],
    )
    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        with pytest.raises(RuntimeError, match="status=3"):
            asyncio.run(provider.generate("test prompt", []))
