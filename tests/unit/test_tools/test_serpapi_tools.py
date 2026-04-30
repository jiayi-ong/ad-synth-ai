from unittest.mock import patch, MagicMock


def test_returns_empty_when_key_absent(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "serpapi_api_key", "")
    from tools.serpapi_tools import (
        search_instagram_trends,
        search_tiktok_trends,
        search_pinterest_trends,
        serpapi_web_search,
    )
    assert search_instagram_trends("test") == []
    assert search_tiktok_trends("test") == []
    assert search_pinterest_trends("test") == []
    assert serpapi_web_search("test") == []


def _make_mock_response(organic_results: list) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"organic_results": organic_results}
    return mock_resp


def test_instagram_normalizes_results(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "serpapi_api_key", "fake-key")

    sample = [{"title": "Post title #running", "snippet": "#running #shoes", "link": "https://instagram.com/p/abc"}]
    with patch("tools.serpapi_tools.httpx.get", return_value=_make_mock_response(sample)):
        from tools.serpapi_tools import search_instagram_trends
        results = search_instagram_trends("running shoes", max_results=5)

    assert len(results) == 1
    assert results[0]["platform"] == "Instagram"
    assert "#running" in results[0]["hashtags"]


def test_tiktok_normalizes_results(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "serpapi_api_key", "fake-key")

    sample = [{"title": "TikTok #running", "snippet": "#running #viral", "link": "https://tiktok.com/@user/video/1"}]
    with patch("tools.serpapi_tools.httpx.get", return_value=_make_mock_response(sample)):
        from tools.serpapi_tools import search_tiktok_trends
        results = search_tiktok_trends("running", max_results=5)

    assert len(results) == 1
    assert results[0]["platform"] == "TikTok"


def test_web_search_normalizes_results(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "serpapi_api_key", "fake-key")

    sample = [{"title": "Best ads 2025", "snippet": "Marketing trends...", "link": "https://example.com"}]
    with patch("tools.serpapi_tools.httpx.get", return_value=_make_mock_response(sample)):
        from tools.serpapi_tools import serpapi_web_search
        results = serpapi_web_search("ad marketing trends", max_results=5)

    assert len(results) == 1
    assert results[0]["title"] == "Best ads 2025"
