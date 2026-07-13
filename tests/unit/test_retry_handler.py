"""
Unit tests for retry handler.
Patches call_llm at src.core.llm.retry_handler.call_llm — the import
used inside retry_handler.py, not the definition location.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch
from src.core.llm.retry_handler import call_with_retry, STRICT_SUFFIX
from src.core.llm.llm_client import LLMProviderError, LLMTimeoutError


PATCH = "src.core.llm.retry_handler.call_llm"


def valid_response_json(**overrides) -> str:
    data = {
        "step_title": "Step 1", "explanation": "Let's go.",
        "question": "What do you know?", "hint": None,
        "final_answer": None, "is_final_step": False,
    }
    data.update(overrides)
    return json.dumps(data)


@pytest.mark.asyncio
async def test_valid_on_first_attempt():
    with patch(PATCH, new=AsyncMock(return_value=valid_response_json())):
        result = await call_with_retry([{"role": "user", "content": "test"}], 0, 5, "s-1")
    assert result.step_title == "Step 1"
    assert result.session_id == "s-1"


@pytest.mark.asyncio
async def test_retry_on_first_failure():
    call_count = 0

    async def mock_llm(messages):
        nonlocal call_count
        call_count += 1
        return "bad json" if call_count == 1 else valid_response_json()

    with patch(PATCH, side_effect=mock_llm):
        result = await call_with_retry([{"role": "user", "content": "test"}], 0, 5, "s-2")
    assert call_count == 2
    assert result.step_title == "Step 1"


@pytest.mark.asyncio
async def test_fallback_on_both_failures():
    with patch(PATCH, new=AsyncMock(return_value="bad json")):
        result = await call_with_retry([{"role": "user", "content": "test"}], 0, 5, "s-3")
    assert result.is_final_step is False
    assert result.final_answer is None
    assert "smaller steps" in result.explanation


@pytest.mark.asyncio
async def test_fallback_on_llm_exception():
    with patch(PATCH, new=AsyncMock(side_effect=LLMProviderError("API down"))):
        result = await call_with_retry([{"role": "user", "content": "test"}], 0, 5, "s-4")
    assert "smaller steps" in result.explanation


@pytest.mark.asyncio
async def test_strict_suffix_added_on_retry():
    call_args = []

    async def mock_llm(messages):
        call_args.append(messages)
        return "bad"

    with patch(PATCH, side_effect=mock_llm):
        await call_with_retry([{"role": "user", "content": "test"}], 0, 5, "s-5")

    assert len(call_args) == 2
    assert STRICT_SUFFIX in call_args[1][-1]["content"]


@pytest.mark.asyncio
async def test_empty_messages_list_does_not_crash():
    """Empty messages list should not raise IndexError — fallback returned."""
    with patch(PATCH, new=AsyncMock(return_value="bad json")):
        result = await call_with_retry([], 0, 5, "s-6")
    assert result is not None
    assert "smaller steps" in result.explanation


@pytest.mark.asyncio
async def test_fallback_on_timeout():
    with patch(PATCH, new=AsyncMock(side_effect=LLMTimeoutError("timed out"))):
        result = await call_with_retry([{"role": "user", "content": "test"}], 0, 5, "s-7")
    assert "smaller steps" in result.explanation
