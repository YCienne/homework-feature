"""
Image Routes — Phase 3
POST /homework/image/extract

Accepts an image upload, runs OCR, returns extracted text for student confirmation.
The student must confirm (or edit) before calling /session/start.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel

from src.api.middleware.auth import AuthenticatedStudent, get_current_student
from src.config.settings import get_settings
from src.core.image.image_extractor import (
    extract_text_from_image,
    ImageUnreadableError,
    ImageTooLargeError,
    ExtractionConfidence,
    ALLOWED_CONTENT_TYPES,
)
from src.store.redis_client import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/homework", tags=["homework"])


class ExtractionResponse(BaseModel):
    extraction_id: str
    extracted_text: str
    confidence: str
    message: str


@router.post("/image/extract", response_model=ExtractionResponse, status_code=200)
async def extract_image(
    image: UploadFile = File(..., description="Image file — JPEG, PNG, or WebP, max 5MB"),
    student: AuthenticatedStudent = Depends(get_current_student),
    redis=Depends(get_redis),
):
    """
    POST /homework/image/extract

    Step 1 of the image input flow. Accepts an image, extracts the text,
    and returns it for the student to confirm or edit before starting a session.

    After confirming, the frontend calls POST /homework/session/start with:
        { "question": "<confirmed or edited text>", "extraction_id": "<id>" }

    The extraction_id expires after 30 minutes.
    """
    settings = get_settings()

    # ── Validate content type ─────────────────────────────────────────────────
    content_type = image.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "INVALID_IMAGE_TYPE",
                "message": f"Please upload a JPEG, PNG, or WebP image.",
            },
        )

    # ── Read and validate file size ───────────────────────────────────────────
    image_bytes = await image.read()
    max_bytes = settings.image_max_size_mb * 1024 * 1024

    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "IMAGE_TOO_LARGE",
                "message": f"Image must be under {settings.image_max_size_mb}MB. Please compress and try again.",
            },
        )

    # ── Extract text via vision model ─────────────────────────────────────────
    try:
        result = await extract_text_from_image(
            image_bytes=image_bytes,
            content_type=content_type,
            redis=redis,
        )
    except ImageUnreadableError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "IMAGE_UNREADABLE",
                "message": str(e),
            },
        )

    # ── Return extracted text for student confirmation ────────────────────────
    confidence_messages = {
        ExtractionConfidence.HIGH: "Text extracted successfully. Please confirm this is correct.",
        ExtractionConfidence.MEDIUM: "Text extracted but some parts may be unclear. Please review and edit if needed.",
    }

    logger.info(
        f"Image extraction complete: student={student.student_id}, "
        f"extraction_id={result.extraction_id}, confidence={result.confidence}"
    )

    return ExtractionResponse(
        extraction_id=result.extraction_id,
        extracted_text=result.extracted_text,
        confidence=result.confidence,
        message=confidence_messages.get(result.confidence, "Please confirm the extracted text."),
    )
