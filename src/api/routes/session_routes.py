import logging
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.middleware.auth import AuthenticatedStudent, get_current_student
from src.api.middleware.rate_limit import check_rate_limit
from src.config.settings import get_settings
from src.config.subjects import SUBJECTS
from src.core.session.session_manager import SessionManager
from src.core.session.session_schema import Session, SessionCreate, StepResponse
from src.core.validator.input_validator import validate_question
from src.core.validator.subject_classifier import classify_subject
from src.core.prompt.prompt_builder import build_prompt
from src.core.llm.retry_handler import call_with_retry
from src.core.image.image_extractor import consume_extraction
from src.store.redis_client import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/homework", tags=["homework"])


@router.post("/session/start", response_model=StepResponse, status_code=200)
async def start_session(
    body: SessionCreate,
    student: AuthenticatedStudent = Depends(check_rate_limit),
    redis=Depends(get_redis),
):
    settings = get_settings()

    # ── Phase 3: If extraction_id provided, verify and consume it ─────────────
    question_source = body.question
    if body.extraction_id:
        confirmed_text = await consume_extraction(body.extraction_id, redis)
        if not confirmed_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "EXTRACTION_EXPIRED",
                    "message": "Your image session expired. Please upload the image again.",
                },
            )
        # Use the confirmed/edited question text (student may have edited it)
        question_source = body.question or confirmed_text

    # 1. Validate input
    validation = validate_question(question_source)
    if not validation.is_valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": validation.error_code, "message": validation.error_message})

    # 2. Classify subject (platform context overrides classifier)
    if body.lesson_subject:
        subject = body.lesson_subject.lower()
        subject_config = SUBJECTS.get(subject, SUBJECTS["general"])
    else:
        subject, subject_config = classify_subject(validation.clean_text)

    # 3. Create session
    session = Session(
        student_id=student.student_id,
        question_raw=body.question,
        question_clean=validation.clean_text,
        subject=subject,
        topic=body.lesson_topic or subject,
        max_steps_allowed=min(subject_config.default_max_steps, settings.max_steps_hard_cap),
    )

    manager = SessionManager(redis)
    await manager.create(session)
    await manager.increment_daily_usage(student.student_id)

    # 4. Build START prompt and call LLM
    messages = build_prompt(action="START", session=session)
    response = await call_with_retry(
        messages=messages,
        current_step_index=session.current_step_index,
        max_steps_allowed=session.max_steps_allowed,
        session_id=session.session_id,
    )

    # 5. Persist the step question so IM_NOT_SURE / EXPLAIN_AGAIN can reference it
    session.last_step_question = response.question or ""
    session.last_step_explanation = response.explanation
    await manager.save(session)

    logger.info(f"Session started: {session.session_id} | subject: {subject}")
    return response


@router.get("/session/{session_id}", status_code=200)
async def get_session(
    session_id: str,
    student: AuthenticatedStudent = Depends(get_current_student),
    redis=Depends(get_redis),
):
    manager = SessionManager(redis)
    session = await manager.get(session_id)

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND",
                    "message": "Your session has expired. Please start a new question."})

    if not manager.verify_ownership(session, student.student_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Access denied."})

    return {
        "session_id": session.session_id,
        "current_step_index": session.current_step_index,
        "max_steps_allowed": session.max_steps_allowed,
        "steps_revealed": session.steps_revealed,
        "is_complete": session.is_complete,
        "subject": session.subject,
        "topic": session.topic,
    }


@router.get("/usage/{student_id}", status_code=200)
async def get_usage(
    student_id: str,
    student: AuthenticatedStudent = Depends(get_current_student),
    redis=Depends(get_redis),
):
    if student.student_id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Access denied."})

    settings = get_settings()
    manager = SessionManager(redis)
    _, used, remaining = await manager.check_daily_limit(student_id)

    return {
        "sessions_today": used,
        "sessions_limit": settings.daily_session_limit,
        "sessions_remaining": remaining,
    }
