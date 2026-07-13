"""
Unit tests for the multi-provider LLM client.
Patches at the call site (_call_gemini / _call_anthropic) to avoid
lru_cache and module-level import issues with get_settings().
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.core.llm.llm_client import (
    call_llm, call_vision,
    LLMProviderError, LLMTimeoutError,
    _call_gemini, _call_anthropic,
    _vision_gemini, _vision_anthropic,
)

MESSAGES = [{"role": "user", "content": "What is gravity?"}]


@pytest.mark.asyncio
async def test_gemini_provider_called():
    with patch("src.core.llm.llm_client._call_gemini", new=AsyncMock(return_value="Gemini answer")) as mock_g:
        with patch("src.core.llm.llm_client.get_settings") as mock_s:
            mock_s.return_value.llm_provider = "gemini"
            result = await call_llm(MESSAGES)
    mock_g.assert_called_once_with(MESSAGES)
    assert result == "Gemini answer"


@pytest.mark.asyncio
async def test_anthropic_provider_called():
    with patch("src.core.llm.llm_client._call_anthropic", new=AsyncMock(return_value="Claude answer")) as mock_a:
        with patch("src.core.llm.llm_client.get_settings") as mock_s:
            mock_s.return_value.llm_provider = "anthropic"
            result = await call_llm(MESSAGES)
    mock_a.assert_called_once_with(MESSAGES)
    assert result == "Claude answer"


@pytest.mark.asyncio
async def test_unknown_provider_raises():
    with patch("src.core.llm.llm_client.get_settings") as mock_s:
        mock_s.return_value.llm_provider = "unknown-provider"
        with pytest.raises(LLMProviderError) as exc:
            await call_llm(MESSAGES)
    assert "unknown-provider" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_vision_gemini_provider():
    with patch("src.core.llm.llm_client._vision_gemini", new=AsyncMock(return_value="extracted")) as mock_v:
        with patch("src.core.llm.llm_client.get_settings") as mock_s:
            mock_s.return_value.image_extraction_provider = "gemini"
            result = await call_vision(b"img", "image/jpeg", "Extract text")
    mock_v.assert_called_once()
    assert result == "extracted"


@pytest.mark.asyncio
async def test_vision_anthropic_provider():
    with patch("src.core.llm.llm_client._vision_anthropic", new=AsyncMock(return_value="extracted")) as mock_v:
        with patch("src.core.llm.llm_client.get_settings") as mock_s:
            mock_s.return_value.image_extraction_provider = "anthropic"
            result = await call_vision(b"img", "image/jpeg", "Extract text")
    mock_v.assert_called_once()
    assert result == "extracted"


@pytest.mark.asyncio
async def test_unknown_vision_provider_raises():
    with patch("src.core.llm.llm_client.get_settings") as mock_s:
        mock_s.return_value.image_extraction_provider = "bad-provider"
        with pytest.raises(LLMProviderError):
            await call_vision(b"img", "image/jpeg", "Extract text")
