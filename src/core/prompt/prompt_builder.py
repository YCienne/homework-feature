"""
Prompt Builder — selects and assembles the correct prompt for each action type.
Returns a messages list ready for call_llm().
"""
import logging
from src.core.session.session_schema import Session
from src.config.subjects import SUBJECTS
from src.core.prompt.templates.action_templates import (
    start_template,
    continue_template,
    im_not_sure_template,
    show_next_step_template,
    explain_again_template,
    finalize_template,
)

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"START", "CONTINUE", "IM_NOT_SURE", "SHOW_NEXT_STEP", "EXPLAIN_AGAIN", "FINALIZE"}


def _to_messages(system: str, user: str) -> list[dict]:
    return [
        {"role": "user", "content": f"[SYSTEM]\n{system}\n\n[USER]\n{user}"}
    ]


def build_prompt(
    action: str,
    session: Session,
    student_response: str | None = None,
) -> list[dict]:
    """
    Builds the messages list for the LLM API call.

    Args:
        action:           START | CONTINUE | IM_NOT_SURE | SHOW_NEXT_STEP | EXPLAIN_AGAIN | FINALIZE
        session:          Current session object
        student_response: Student's typed answer — required for CONTINUE

    Returns:
        list[dict]: Anthropic-compatible messages list
    """
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unknown action: {action}. Must be one of {VALID_ACTIONS}")

    subject_config = SUBJECTS.get(session.subject, SUBJECTS["general"])
    ctx = subject_config.curriculum_context

    history_dicts = [r.model_dump() for r in session.step_history]

    if action == "START":
        system, user = start_template(
            question_clean=session.question_clean,
            subject=session.subject,
            topic=session.topic,
            max_steps=session.max_steps_allowed,
            curriculum_context=ctx,
        )

    elif action == "CONTINUE":
        is_last = session.current_step_index >= session.max_steps_allowed - 1
        system, user = continue_template(
            question_clean=session.question_clean,
            subject=session.subject,
            current_step=session.current_step_index,
            max_steps=session.max_steps_allowed,
            step_history=history_dicts,
            student_response=student_response or "",
            curriculum_context=ctx,
            is_last_step=is_last,
        )

    elif action == "IM_NOT_SURE":
        system, user = im_not_sure_template(
            question_clean=session.question_clean,
            current_step_question=session.last_step_question,
            subject=session.subject,
            curriculum_context=ctx,
        )

    elif action == "SHOW_NEXT_STEP":
        system, user = show_next_step_template(
            question_clean=session.question_clean,
            current_step=session.current_step_index,
            max_steps=session.max_steps_allowed,
            step_history=history_dicts,
            curriculum_context=ctx,
            subject=session.subject,
        )

    elif action == "EXPLAIN_AGAIN":
        system, user = explain_again_template(
            question_clean=session.question_clean,
            current_step_explanation=session.last_step_explanation,
            current_step_question=session.last_step_question,
            subject=session.subject,
            curriculum_context=ctx,
        )

    elif action == "FINALIZE":
        system, user = finalize_template(
            question_clean=session.question_clean,
            subject=session.subject,
            step_history=history_dicts,
            curriculum_context=ctx,
        )

    logger.debug(f"Prompt built for action={action}, session={session.session_id}")
    return _to_messages(system, user)
