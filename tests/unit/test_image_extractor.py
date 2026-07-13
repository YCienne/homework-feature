import pytest
from unittest.mock import AsyncMock, patch
from src.core.image.image_extractor import (
    extract_text_from_image,
    consume_extraction,
    get_extracted_text,
    _assess_confidence,
    ExtractionConfidence,
    ImageUnreadableError,
    ALLOWED_CONTENT_TYPES,
)


# ── Confidence assessment tests ───────────────────────────────────────────────

def test_confidence_high_for_clear_text():
    text = "What is the area of a triangle with base 5cm and height 3cm?"
    assert _assess_confidence(text, b"x" * 5000) == ExtractionConfidence.HIGH


def test_confidence_medium_for_unclear_markers():
    text = "What is [unclear] of a triangle with base [unclear] cm?"
    assert _assess_confidence(text, b"x" * 5000) == ExtractionConfidence.MEDIUM


def test_confidence_low_for_empty():
    assert _assess_confidence("", b"x" * 5000) == ExtractionConfidence.LOW


def test_confidence_low_for_very_short():
    assert _assess_confidence("hi", b"x" * 5000) == ExtractionConfidence.LOW


def test_confidence_low_for_many_unclear():
    text = "[unclear] [unclear] [unclear] something"
    assert _assess_confidence(text, b"x" * 5000) == ExtractionConfidence.LOW


# ── extract_text_from_image tests ─────────────────────────────────────────────

@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.setex = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest.mark.asyncio
async def test_extract_success(mock_redis):
    extracted = "What is the area of a rectangle with width 4 and height 6?"
    with patch("src.core.image.image_extractor.call_vision", new=AsyncMock(return_value=extracted)):
        result = await extract_text_from_image(
            image_bytes=b"x" * 5000,
            content_type="image/jpeg",
            redis=mock_redis,
        )
    assert result.extracted_text == extracted
    assert result.confidence == ExtractionConfidence.HIGH
    assert result.extraction_id is not None
    mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_extract_invalid_content_type(mock_redis):
    with pytest.raises(ImageUnreadableError):
        await extract_text_from_image(b"data", "image/gif", mock_redis)


@pytest.mark.asyncio
async def test_extract_image_too_small(mock_redis):
    with pytest.raises(ImageUnreadableError):
        await extract_text_from_image(b"tiny", "image/jpeg", mock_redis)


@pytest.mark.asyncio
async def test_extract_low_confidence_raises(mock_redis):
    with patch("src.core.image.image_extractor.call_vision", new=AsyncMock(return_value="")):
        with pytest.raises(ImageUnreadableError) as exc:
            await extract_text_from_image(b"x" * 5000, "image/jpeg", mock_redis)
    assert "clearly" in str(exc.value).lower() or "type" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_extract_vision_error_raises(mock_redis):
    from src.core.llm.llm_client import LLMProviderError
    with patch("src.core.image.image_extractor.call_vision", new=AsyncMock(side_effect=LLMProviderError("API down"))):
        with pytest.raises(ImageUnreadableError):
            await extract_text_from_image(b"x" * 5000, "image/jpeg", mock_redis)


# ── Consume extraction tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_consume_extraction_found(mock_redis):
    mock_redis.get = AsyncMock(return_value="What is gravity?")
    text = await consume_extraction("some-id", mock_redis)
    assert text == "What is gravity?"
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_consume_extraction_not_found(mock_redis):
    mock_redis.get = AsyncMock(return_value=None)
    text = await consume_extraction("expired-id", mock_redis)
    assert text is None
    mock_redis.delete.assert_not_called()


@pytest.mark.asyncio
async def test_get_extracted_text_found(mock_redis):
    mock_redis.get = AsyncMock(return_value="Some question text")
    text = await get_extracted_text("some-id", mock_redis)
    assert text == "Some question text"
