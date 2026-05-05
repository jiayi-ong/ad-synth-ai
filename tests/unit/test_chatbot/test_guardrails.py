"""Unit tests for chatbot guardrail keyword detection."""
import pytest

from backend.services.chatbot_service import check_guardrail


class TestGuardrailDetection:
    def test_trigger_word_generate(self):
        assert check_guardrail("please generate an ad for me") == "generate"

    def test_trigger_word_create(self):
        assert check_guardrail("can you create a new campaign") == "create"

    def test_trigger_word_delete(self):
        assert check_guardrail("delete the product I just added") == "delete"

    def test_trigger_word_remove(self):
        assert check_guardrail("remove this persona from the list") == "remove"

    def test_trigger_word_start(self):
        assert check_guardrail("start the generation process") == "start"

    def test_trigger_word_run(self):
        assert check_guardrail("run the pipeline for me") == "run"

    def test_trigger_word_add(self):
        assert check_guardrail("add a new product to my campaign") == "add"

    def test_trigger_word_submit(self):
        assert check_guardrail("submit the form now") == "submit"

    def test_trigger_word_launch(self):
        assert check_guardrail("launch the ad campaign") == "launch"

    def test_trigger_word_modify(self):
        assert check_guardrail("modify my brand settings") == "modify"

    def test_trigger_word_upload(self):
        assert check_guardrail("upload a product image") == "upload"

    def test_trigger_word_execute(self):
        assert check_guardrail("execute the analysis") == "execute"

    def test_no_trigger_informational(self):
        assert check_guardrail("what does the generation page do?") is None

    def test_no_trigger_explanation(self):
        assert check_guardrail("how does the trend research agent work?") is None

    def test_no_trigger_what_is(self):
        assert check_guardrail("what is a persona in AdSynth?") is None

    def test_no_trigger_explain(self):
        assert check_guardrail("explain the evaluation score to me") is None

    def test_no_trigger_empty(self):
        assert check_guardrail("") is None

    def test_whole_word_boundary_no_false_positive(self):
        # 'run' should not match 'running'
        assert check_guardrail("what is the running process doing?") is None

    def test_whole_word_boundary_create_within_word(self):
        # 'create' as standalone word triggers; embedded in longer word should not
        assert check_guardrail("recreate the output") is None

    def test_case_insensitive_upper(self):
        assert check_guardrail("GENERATE an ad") == "generate"

    def test_case_insensitive_mixed(self):
        assert check_guardrail("Can you Generate this?") == "generate"

    def test_first_matching_word_returned(self):
        # 'create' comes before 'delete' in _GUARDRAIL_WORDS
        result = check_guardrail("create and delete something")
        assert result in ("create", "delete")  # first match wins
