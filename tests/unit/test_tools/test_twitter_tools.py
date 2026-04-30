from unittest.mock import MagicMock, patch


def test_returns_empty_when_both_keys_absent(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "twitter_bearer_token", "")
    monkeypatch.setattr(settings, "serpapi_api_key", "")
    from tools.twitter_tools import search_twitter_trends
    assert search_twitter_trends("running shoes") == []


def test_returns_results_from_tweepy(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "twitter_bearer_token", "fake-bearer")

    mock_tweet = MagicMock()
    mock_tweet.text = "Love these running shoes! #running"
    mock_tweet.public_metrics = {"like_count": 500, "retweet_count": 100, "reply_count": 20}
    mock_tweet.created_at = None

    mock_response = MagicMock()
    mock_response.data = [mock_tweet]

    mock_client = MagicMock()
    mock_client.search_recent_tweets.return_value = mock_response

    with patch("tools.twitter_tools.tweepy") as mock_tweepy:
        mock_tweepy.Client.return_value = mock_client
        from tools.twitter_tools import search_twitter_trends
        results = search_twitter_trends("running shoes", max_results=5)

    assert len(results) == 1
    assert results[0]["like_count"] == 500
    assert results[0]["source"] == "twitter_api"


def test_falls_back_to_serpapi_on_rate_limit(monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "twitter_bearer_token", "fake-bearer")
    monkeypatch.setattr(settings, "serpapi_api_key", "fake-serpapi")

    with patch("tools.twitter_tools.tweepy") as mock_tweepy, \
         patch("tools.twitter_tools._serpapi_twitter_search", return_value=[{"text": "fallback", "source": "serpapi"}]) as mock_fallback:
        mock_tweepy.Client.return_value.search_recent_tweets.side_effect = Exception("429 Too Many Requests")
        mock_tweepy.errors = MagicMock()
        mock_tweepy.errors.TooManyRequests = Exception

        from tools.twitter_tools import search_twitter_trends
        results = search_twitter_trends("test")

    mock_fallback.assert_called_once()
    assert results[0]["source"] == "serpapi"
