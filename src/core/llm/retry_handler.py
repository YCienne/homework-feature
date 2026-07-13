import logging
from src.core.session.session_schema import StepResponse
from src.core.llm.llm_client import call_llm, LLMTimeoutError, LLMProviderError
from src.core.llm.response_validator import validate_llm_response

logger = logging.getLogger(__name__)

STRICT_SUFFIX = (
    "\n\nCRITICAL REMINDER: You MUST respond ONLY with a valid JSON object. "
    "No markdown, no explanation, no text outside the JSON braces. "
    "The 'question' field is required on every non-final step. "
    "Do NOT set final_answer unless is_final_step is true."
)


def _fallback(session_id: str) -> StepResponse:
    return StepResponse(
        session_id=session_id,
        step_title="Let's slow down",
        explanation="Let's break this into smaller steps.",
        question="Can you tell me what you already know about this problem?",
        hint=None,
        final_answer=None,
        is_final_step=False,
    )


def _dict_to_response(session_id: str, data: dict) -> StepResponse:
    return StepResponse(
        session_id=session_id,
        step_title=data.get("step_title", ""),
        explanation=data.get("explanation", ""),
        question=data.get("question"),
        hint=data.get("hint"),
        final_answer=data.get("final_answer"),
        is_final_step=bool(data.get("is_final_step", False)),
    )


async def call_with_retry(
    messages: list[dict],
    current_step_index: int,
    max_steps_allowed: int,
    session_id: str,
) -> StepResponse:
    """
    Calls the LLM, validates, retries once with a stricter prompt if invalid,
    and returns a fallback if still invalid. Never raises.
    """
    # ── Attempt 1 ─────────────────────────────────────────────────────────────
    try:
        raw = await call_llm(messages)
        result = validate_llm_response(raw, current_step_index, max_steps_allowed)
        if result.is_valid:
            logger.info(f"LLM response valid on first attempt (session: {session_id})")
            return _dict_to_response(session_id, result.parsed)
        logger.warning(f"First attempt invalid: {result.failure_reason} — retrying")
    except (LLMTimeoutError, LLMProviderError) as e:
        logger.error(f"LLM call failed on attempt 1: {e}")

    # ── Attempt 2 — stricter prompt ───────────────────────────────────────────
    try:
        strict_messages = messages.copy()
        # Append strict reminder to the last user message (guard against empty list)
        if strict_messages:
            last = strict_messages[-1]
            strict_messages[-1] = {
                "role": last["role"],
                "content": last["content"] + STRICT_SUFFIX,
            }
        else:
            # No messages supplied — send strict suffix as a standalone prompt
            strict_messages = [{"role": "user", "content": STRICT_SUFFIX}]
        raw2 = await call_llm(strict_messages)
        result2 = validate_llm_response(raw2, current_step_index, max_steps_allowed)
        if result2.is_valid:
            logger.info(f"LLM response valid on retry (session: {session_id})")
            return _dict_to_response(session_id, result2.parsed)
        logger.error(f"Retry also invalid: {result2.failure_reason} — using fallback")
    except (LLMTimeoutError, LLMProviderError) as e:
        logger.error(f"LLM call failed on attempt 2: {e}")

    # ── Fallback ──────────────────────────────────────────────────────────────
    logger.warning(f"Returning fallback response for session: {session_id}")
    return _fallback(session_id)
