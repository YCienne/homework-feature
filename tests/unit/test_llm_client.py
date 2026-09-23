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
    _call_gemini, _call_anthropic, _call_anthropic_aws, _call_bedrock,
    _vision_gemini, _vision_anthropic,
    _split_system,
)

MESSAGES = [{"role": "user", "content": "What is gravity?"}]
SPLIT_MESSAGES = [
    {"role": "system", "content": "You are a tutor."},
    {"role": "user", "content": "What is gravity?"},
]


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
async def test_anthropic_aws_provider_called():
    with patch("src.core.llm.llm_client._call_anthropic_aws", new=AsyncMock(return_value="Claude AWS answer")) as mock_a:
        with patch("src.core.llm.llm_client.get_settings") as mock_s:
            mock_s.return_value.llm_provider = "anthropic_aws"
            result = await call_llm(MESSAGES)
    mock_a.assert_called_once_with(MESSAGES)
    assert result == "Claude AWS answer"


@pytest.mark.asyncio
async def test_bedrock_provider_called():
    with patch("src.core.llm.llm_client._call_bedrock", new=AsyncMock(return_value="Bedrock answer")) as mock_b:
        with patch("src.core.llm.llm_client.get_settings") as mock_s:
            mock_s.return_value.llm_provider = "bedrock"
            result = await call_llm(MESSAGES)
    mock_b.assert_called_once_with(MESSAGES)
    assert result == "Bedrock answer"


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


def test_split_system_extracts_system_message():
    system, rest = _split_system(SPLIT_MESSAGES)
    assert system == "You are a tutor."
    assert rest == [{"role": "user", "content": "What is gravity?"}]


def test_split_system_returns_none_when_absent():
    system, rest = _split_system(MESSAGES)
    assert system is None
    assert rest == MESSAGES


@pytest.mark.asyncio
async def test_call_anthropic_passes_system_param_separately():
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=MagicMock(content=[MagicMock(text="ok")]))
    with patch("src.core.llm.llm_client._get_anthropic_client", return_value=mock_client):
        with patch("src.core.llm.llm_client.get_settings") as mock_s:
            mock_s.return_value.llm_model_anthropic = "claude-sonnet-4-20250514"
            result = await _call_anthropic(SPLIT_MESSAGES)

    assert result == "ok"
    _, kwargs = mock_client.messages.create.call_args
    assert kwargs["system"] == "You are a tutor."
    assert kwargs["messages"] == [{"role": "user", "content": "What is gravity?"}]


@pytest.mark.asyncio
async def test_call_anthropic_aws_passes_system_param_separately():
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=MagicMock(content=[MagicMock(text="ok")]))
    with patch("src.core.llm.llm_client._get_anthropic_aws_client", return_value=mock_client):
        with patch("src.core.llm.llm_client.get_settings") as mock_s:
            mock_s.return_value.llm_model_anthropic = "claude-sonnet-4-20250514"
            result = await _call_anthropic_aws(SPLIT_MESSAGES)

    assert result == "ok"
    _, kwargs = mock_client.messages.create.call_args
    assert kwargs["system"] == "You are a tutor."
    assert kwargs["messages"] == [{"role": "user", "content": "What is gravity?"}]


def test_get_anthropic_aws_client_requires_region():
    import src.core.llm.llm_client as llm_client
    llm_client._anthropic_aws_client = None
    with patch("src.core.llm.llm_client.get_settings") as mock_s:
        mock_s.return_value.claude_aws_region = ""
        with pytest.raises(LLMProviderError):
            llm_client._get_anthropic_aws_client()


@pytest.mark.asyncio
async def test_call_bedrock_converse_and_system_block():
    mock_client = MagicMock()
    mock_client.converse.return_value = {
        "output": {"message": {"content": [{"text": "ok"}]}}
    }
    with patch("src.core.llm.llm_client._get_bedrock_client", return_value=mock_client):
        with patch("src.core.llm.llm_client.get_settings") as mock_s:
            mock_s.return_value.bedrock_model_id = "anthropic.claude-haiku-4-5-20251001-v1:0"
            result = await _call_bedrock(SPLIT_MESSAGES)

    assert result == "ok"
    _, kwargs = mock_client.converse.call_args
    assert kwargs["modelId"] == "anthropic.claude-haiku-4-5-20251001-v1:0"
    assert kwargs["system"] == [{"text": "You are a tutor."}]
    assert kwargs["messages"] == [{"role": "user", "content": [{"text": "What is gravity?"}]}]


def test_get_bedrock_client_requires_region():
    import src.core.llm.llm_client as llm_client
    llm_client._bedrock_client = None
    with patch("src.core.llm.llm_client.get_settings") as mock_s:
        mock_s.return_value.bedrock_region = ""
        with pytest.raises(LLMProviderError):
            llm_client._get_bedrock_client()


@pytest.mark.asyncio
async def test_call_bedrock_requires_model_id():
    with patch("src.core.llm.llm_client.get_settings") as mock_s:
        mock_s.return_value.bedrock_model_id = ""
        with pytest.raises(LLMProviderError):
            await _call_bedrock(MESSAGES)
