"""
Image Extractor — Phase 3
Accepts image bytes, runs OCR via vision model, returns extracted text.

Flow (per spec Section 12):
  Image Upload → Validate → OCR → Return text + confidence
  → Student confirms/edits → /session/start called with extraction_id

Rules:
  - Never process image directly into a solution
  - Always convert image → text first
  - Store extraction result in Redis with short TTL (30 min)
  - Require confirmation token before homework session starts
"""
import uuid
import logging
from dataclasses import dataclass
from enum import Enum

from src.core.llm.llm_client import call_vision, LLMProviderError

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

EXTRACTION_PROMPT = """You are an OCR assistant. Extract ALL text from this image exactly as it appears.

Rules:
- Preserve mathematical symbols, equations, and formatting as closely as possible
- Do not solve or interpret the problem — only transcribe the text
- If the image contains a diagram, describe it briefly in [brackets] after the text
- If you cannot read part of the text clearly, indicate with [unclear]
- Return ONLY the extracted text, nothing else — no preamble, no explanation"""


class ExtractionConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ExtractionResult:
    extraction_id: str
    extracted_text: str
    confidence: ExtractionConfidence


def _assess_confidence(extracted_text: str, image_bytes: bytes) -> ExtractionConfidence:
    """
    Heuristic confidence scoring based on extracted text quality.
    - HIGH:   Meaningful text extracted, reasonable length
    - MEDIUM: Short text or contains [unclear] markers
    - LOW:    Very short, mostly unclear, or looks like extraction failed
    """
    text = extracted_text.strip()

    if not text or len(text) < 10:
        return ExtractionConfidence.LOW

    unclear_count = text.lower().count("[unclear]")
    word_count = len(text.split())

    if unclear_count >= 3 or word_count < 3:
        return ExtractionConfidence.LOW

    if unclear_count >= 1 or word_count < 8:
        return ExtractionConfidence.MEDIUM

    return ExtractionConfidence.HIGH


async def extract_text_from_image(
    image_bytes: bytes,
    content_type: str,
    redis,
) -> ExtractionResult:
    """
    Validates image, runs OCR via vision model, stores result in Redis.

    Args:
        image_bytes:  Raw image bytes from upload
        content_type: MIME type (image/jpeg, image/png, image/webp)
        redis:        Redis client for storing extraction result

    Returns:
        ExtractionResult with extraction_id, extracted_text, confidence

    Raises:
        ImageUnreadableError: If content_type invalid, image too small, or confidence LOW
        ImageTooLargeError:   If image exceeds size limit (checked before calling this)
    """
    # ── Validate content type ─────────────────────────────────────────────────
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ImageUnreadableError(
            f"Unsupported image type: {content_type}. "
            f"Please upload a JPEG, PNG, or WebP image."
        )

    # ── Validate image is not empty ───────────────────────────────────────────
    if len(image_bytes) < 1000:
        raise ImageUnreadableError("Image is too small or corrupted.")

    # ── Call vision model ─────────────────────────────────────────────────────
    try:
        extracted_text = await call_vision(
            image_bytes=image_bytes,
            content_type=content_type,
            prompt=EXTRACTION_PROMPT,
        )
    except LLMProviderError as e:
        logger.error(f"Vision model error during extraction: {e}")
        raise ImageUnreadableError("Could not process the image. Please try again or type your question.")

    # ── Assess confidence ─────────────────────────────────────────────────────
    confidence = _assess_confidence(extracted_text, image_bytes)

    if confidence == ExtractionConfidence.LOW:
        logger.warning(f"Low confidence extraction: '{extracted_text[:80]}'")
        raise ImageUnreadableError(
            "Sorry, I couldn't read this clearly. Please type the question."
        )

    # ── Store in Redis with short TTL (student must confirm within 30 min) ────
    extraction_id = str(uuid.uuid4())
    from src.config.settings import get_settings
    settings = get_settings()
    redis_key = f"hw:extraction:{extraction_id}"

    await redis.setex(
        redis_key,
        settings.image_extraction_ttl_seconds,
        extracted_text,
    )

    logger.info(
        f"Image extracted successfully: id={extraction_id}, "
        f"confidence={confidence}, length={len(extracted_text)} chars"
    )

    return ExtractionResult(
        extraction_id=extraction_id,
        extracted_text=extracted_text,
        confidence=confidence,
    )


async def get_extracted_text(extraction_id: str, redis) -> str | None:
    """
    Retrieves confirmed extraction text from Redis by extraction_id.
    Returns None if the token has expired or does not exist.
    Used by session/start to verify the confirmation token.
    """
    redis_key = f"hw:extraction:{extraction_id}"
    text = await redis.get(redis_key)
    return text


async def consume_extraction(extraction_id: str, redis) -> str | None:
    """
    Retrieves and deletes the extraction from Redis (one-time use token).
    Called when session/start consumes the confirmed extraction.
    """
    redis_key = f"hw:extraction:{extraction_id}"
    text = await redis.get(redis_key)
    if text:
        await redis.delete(redis_key)
    return text


class ImageUnreadableError(Exception):
    """Raised when image cannot be read or confidence is too low."""
    pass


class ImageTooLargeError(Exception):
    """Raised when image exceeds the configured size limit."""
    pass
