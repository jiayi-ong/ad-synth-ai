"""Verify state_keys module integrity."""
from backend.pipeline.state_keys import AGENT_OUTPUT_KEYS, IMAGE_GEN_PROMPT, PRODUCT_PROFILE


def test_agent_output_keys_count():
    assert len(AGENT_OUTPUT_KEYS) == 11


def test_state_keys_are_strings():
    assert isinstance(PRODUCT_PROFILE, str)
    assert isinstance(IMAGE_GEN_PROMPT, str)


def test_all_keys_unique():
    assert len(AGENT_OUTPUT_KEYS) == len(set(AGENT_OUTPUT_KEYS))
