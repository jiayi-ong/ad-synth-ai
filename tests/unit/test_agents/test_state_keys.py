"""Verify state_keys module integrity."""
from backend.pipeline.state_keys import AGENT_OUTPUT_KEYS, IMAGE_GEN_PROMPT, PRODUCT_PROFILE


def test_agent_output_keys_count():
    assert len(AGENT_OUTPUT_KEYS) == 7


def test_state_keys_are_strings():
    assert isinstance(PRODUCT_PROFILE, str)
    assert isinstance(IMAGE_GEN_PROMPT, str)


def test_all_keys_unique():
    assert len(AGENT_OUTPUT_KEYS) == len(set(AGENT_OUTPUT_KEYS))


def test_trend_sub_pipeline_keys_exist():
    from backend.pipeline.state_keys import (
        AGGREGATED_TREND_DATA,
        INSTAGRAM_TREND_DATA,
        PINTEREST_TREND_DATA,
        REDDIT_TREND_DATA,
        TIKTOK_TREND_DATA,
        TREND_KEYWORDS,
        TWITTER_TREND_DATA,
        WEB_SEARCH_TREND_DATA,
        YOUTUBE_TREND_DATA,
    )
    assert TREND_KEYWORDS == "trend_keywords"
    assert YOUTUBE_TREND_DATA == "youtube_trend_data"
    assert TWITTER_TREND_DATA == "twitter_trend_data"
    assert TIKTOK_TREND_DATA == "tiktok_trend_data"
    assert INSTAGRAM_TREND_DATA == "instagram_trend_data"
    assert REDDIT_TREND_DATA == "reddit_trend_data"
    assert WEB_SEARCH_TREND_DATA == "web_search_trend_data"
    assert PINTEREST_TREND_DATA == "pinterest_trend_data"
    assert AGGREGATED_TREND_DATA == "aggregated_trend_data"
    # Verify none of these are in AGENT_OUTPUT_KEYS (they are sub-pipeline internal keys)
    sub_keys = {
        TREND_KEYWORDS, YOUTUBE_TREND_DATA, TWITTER_TREND_DATA,
        TIKTOK_TREND_DATA, INSTAGRAM_TREND_DATA, REDDIT_TREND_DATA,
        WEB_SEARCH_TREND_DATA, PINTEREST_TREND_DATA, AGGREGATED_TREND_DATA,
    }
    assert not sub_keys.intersection(set(AGENT_OUTPUT_KEYS))
