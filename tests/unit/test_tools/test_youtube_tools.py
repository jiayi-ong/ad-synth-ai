from unittest.mock import MagicMock, patch


def test_returns_empty_when_key_absent(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "youtube_api_key", "")
    from tools.youtube_tools import search_youtube_trends
    assert search_youtube_trends("running shoes") == []


def test_returns_normalized_results_when_api_succeeds(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "youtube_api_key", "fake-key")

    mock_search_resp = {
        "items": [{"id": {"videoId": "abc123"}}]
    }
    mock_stats_resp = {
        "items": [
            {
                "id": "abc123",
                "snippet": {
                    "title": "Best Running Shoes 2025",
                    "channelTitle": "RunnerChannel",
                    "publishedAt": "2025-01-01T00:00:00Z",
                },
                "statistics": {
                    "viewCount": "1000000",
                    "likeCount": "50000",
                    "commentCount": "3000",
                },
            }
        ]
    }

    mock_youtube = MagicMock()
    mock_youtube.search().list().execute.return_value = mock_search_resp
    mock_youtube.videos().list().execute.return_value = mock_stats_resp

    with patch("tools.youtube_tools.build", return_value=mock_youtube):
        from tools.youtube_tools import search_youtube_trends
        results = search_youtube_trends("running shoes", max_results=5)

    assert len(results) == 1
    assert results[0]["video_id"] == "abc123"
    assert results[0]["view_count"] == 1000000
    assert results[0]["title"] == "Best Running Shoes 2025"


def test_returns_empty_on_api_error(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "youtube_api_key", "fake-key")

    with patch("tools.youtube_tools.build", side_effect=Exception("API error")):
        from tools.youtube_tools import search_youtube_trends
        assert search_youtube_trends("test") == []
