import logging
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.middleware.auth import AuthenticatedStudent, get_current_student
from src.core.session.session_manager import SessionManager
from src.core.session.session_schema import ActionRequest, StepResponse
from src.core.prompt.prompt_builder import build_prompt
from src.core.llm.retry_handler import call_with_retry
from src.core.tracking.concept_tracker import record_concept
from src.store.redis_client import get_redis
from src.store.db_client import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/homework", tags=["homework"])

VALID_ACTIONS = {"CONTINUE", "IM_NOT_SURE", "SHOW_NEXT_STEP", "EXPLAIN_AGAIN"}
SKIP_GUARDRAIL_THRESHOLD = 3


@router.post("/session/{session_id}/action", response_model=StepResponse, status_code=200)
async def session_action(
    session_id: str,
    body: ActionRequest,
    student: AuthenticatedStudent = Depends(get_current_student),
    redis=Depends(get_redis),
    db=Depends(get_db_session),
):
    # ── Validate action ───────────────────────────────────────────────────────
    if body.action not in VALID_ACTIONS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "INVALID_ACTION",
                    "message": f"Action must be one of: {', '.join(VALID_ACTIONS)}"})

    if body.action == "CONTINUE" and not body.response:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "MISSING_RESPONSE",
                    "message": "Please provide your answer before continuing."})

    # ── Load session ──────────────────────────────────────────────────────────
    manager = SessionManager(redis)
    session = await manager.get(session_id)

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND",
                    "message": "Your session has expired. Please start a new question."})

    if not manager.verify_ownership(session, student.student_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Access denied."})

    if session.is_complete:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "SESSION_COMPLETE",
                    "message": "This session is already complete. Start a new question!"})

    # ── SHOW_NEXT_STEP — guardrail check ──────────────────────────────────────
    if body.action == "SHOW_NEXT_STEP":
        await manager.record_skip_attempt(session)
        if session.skip_attempts >= SKIP_GUARDRAIL_THRESHOLD:
            logger.info(f"Skip guardrail triggered: session={session_id}, attempts={session.skip_attempts}")
            return StepResponse(
                session_id=session_id,
                step_title="Let's try this step",
                explanation="Try this step first before moving on.",
                question=session.last_step_question or "What do you think the next part might be?",
                hint="Look back at what we've covered — you're closer than you think.",
                final_answer=None,
                is_final_step=False,
            )

    # ── IM_NOT_SURE — record hint usage ──────────────────────────────────────
    if body.action == "IM_NOT_SURE":
        await manager.record_hint_used(session)

    # ── Build prompt ──────────────────────────────────────────────────────────
    messages = build_prompt(
        action=body.action,
        session=session,
        student_response=body.response,
    )

    # ── Call LLM with retry ───────────────────────────────────────────────────
    response = await call_with_retry(
        messages=messages,
        current_step_index=session.current_step_index,
        max_steps_allowed=session.max_steps_allowed,
        session_id=session_id,
    )

    # ── Update session state based on action and response ─────────────────────
    if body.action == "CONTINUE":
        if response.is_final_step:
            if session.current_step_index >= session.max_steps_allowed - 1:
                await manager.advance_step(session, session.last_step_question, body.response)
                await manager.complete_session(session)
                # Phase 4: write concept tag (fire-and-forget — never blocks response)
                await record_concept(
                    db=db,
                    student_id=student.student_id,
                    session_id=session_id,
                    subject=session.subject,
                    topic=session.topic,
                    completed=True,
                    steps_needed=session.steps_revealed + 1,
                    hints_used=session.hints_used,
                    skips_used=session.skips_used,
                )
                logger.info(f"Session completed and concept tracked: {session_id}")
            else:
                logger.warning(f"LLM tried to finalize early at step {session.current_step_index} — advancing normally")
                response.is_final_step = False
                response.final_answer = None
                await manager.advance_step(session, session.last_step_question, body.response)
        else:
            await manager.advance_step(session, session.last_step_question, body.response)

    elif body.action == "SHOW_NEXT_STEP":
        # Skip was allowed (fewer than SKIP_GUARDRAIL_THRESHOLD consecutive skips) — advance step
        await manager.advance_step(session, session.last_step_question, None)

    # ── Persist the new step's question for next IM_NOT_SURE / EXPLAIN_AGAIN ──
    if response.question:
        session.last_step_question = response.question
    if response.explanation:
        session.last_step_explanation = response.explanation
    await manager.save(session)

    return response
