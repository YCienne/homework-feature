import json
import pytest
from src.core.llm.response_validator import validate_llm_response


def valid_json(**overrides) -> str:
    data = {
        "step_title": "Step 1",
        "explanation": "Let's start here.",
        "question": "What do you know about fractions?",
        "hint": None,
        "final_answer": None,
        "is_final_step": False,
    }
    data.update(overrides)
    return json.dumps(data)


def test_valid_response():
    r = validate_llm_response(valid_json(), current_step_index=0, max_steps_allowed=5)
    assert r.is_valid is True
    assert r.parsed is not None


def test_malformed_json():
    r = validate_llm_response("this is not json", 0, 5)
    assert r.is_valid is False
    assert r.failure_reason == "MALFORMED_JSON"


def test_strips_markdown_fences():
    raw = "```json\n" + valid_json() + "\n```"
    r = validate_llm_response(raw, 0, 5)
    assert r.is_valid is True


def test_premature_final_answer_stripped():
    raw = valid_json(final_answer="The answer is 42", is_final_step=False)
    r = validate_llm_response(raw, 0, 5)
    assert r.is_valid is True
    assert r.parsed["final_answer"] is None


def test_step_gate_overrides_early_finalize():
    raw = valid_json(is_final_step=True, final_answer="42", question=None)
    r = validate_llm_response(raw, current_step_index=0, max_steps_allowed=5)
    assert r.is_valid is True
    assert r.parsed["is_final_step"] is False
    assert r.parsed["final_answer"] is None


def test_missing_question_on_non_final_step():
    raw = valid_json(question=None, is_final_step=False)
    r = validate_llm_response(raw, 0, 5)
    assert r.is_valid is False
    assert r.failure_reason == "MISSING_QUESTION"


def test_explanation_truncated_if_too_long():
    long_explanation = "x" * 500
    raw = valid_json(explanation=long_explanation)
    r = validate_llm_response(raw, 0, 5)
    assert r.is_valid is True
    assert len(r.parsed["explanation"]) == 400


def test_valid_final_step():
    raw = valid_json(is_final_step=True, final_answer="The answer is 10", question=None)
    r = validate_llm_response(raw, current_step_index=4, max_steps_allowed=5)
    assert r.is_valid is True
    assert r.parsed["is_final_step"] is True
    assert r.parsed["final_answer"] == "The answer is 10"


def test_missing_required_fields():
    r = validate_llm_response(json.dumps({"step_title": "Step 1"}), 0, 5)
    assert r.is_valid is False
    assert "MISSING_FIELDS" in r.failure_reason
