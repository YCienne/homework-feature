import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

MAX_EXPLANATION_LENGTH = 400
REQUIRED_FIELDS = {"step_title", "explanation", "is_final_step"}


@dataclass
class ResponseValidationResult:
    is_valid: bool
    parsed: Optional[dict] = None
    failure_reason: Optional[str] = None


def validate_llm_response(
    raw_response: str,
    current_step_index: int,
    max_steps_allowed: int,
) -> ResponseValidationResult:
    """
    Validates LLM raw response against all 6 rules from the API spec.

    Rule 1 — Schema conformance:  required fields present
    Rule 2 — Premature answer:    final_answer null unless is_final_step true
    Rule 3 — Step gate:           is_final_step cannot be true before max steps
    Rule 4 — Question presence:   question required when not final step
    Rule 5 — Length:              explanation <= 400 chars
    Rule 6 — Valid JSON:          must parse cleanly
    """
    # Rule 6 — JSON parse
    try:
        # Strip markdown fences if model wraps in ```json ... ```
        text = raw_response.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
    except (json.JSONDecodeError, IndexError) as e:
        logger.warning(f"JSON parse failed: {e} | raw: {raw_response[:200]}")
        return ResponseValidationResult(is_valid=False, failure_reason="MALFORMED_JSON")

    if not isinstance(data, dict):
        return ResponseValidationResult(is_valid=False, failure_reason="NOT_A_DICT")

    # Rule 1 — Required fields
    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        logger.warning(f"Missing fields: {missing}")
        return ResponseValidationResult(is_valid=False, failure_reason=f"MISSING_FIELDS:{missing}")

    is_final = bool(data.get("is_final_step", False))
    final_answer = data.get("final_answer")
    question = data.get("question")
    explanation = data.get("explanation", "")

    # Rule 2 — Premature answer
    if final_answer and not is_final:
        logger.warning("final_answer populated but is_final_step is false — stripping")
        data["final_answer"] = None

    # Rule 3 — Step gate: is_final_step true too early
    if is_final and current_step_index < max_steps_allowed - 1:
        logger.warning(
            f"is_final_step=true at step {current_step_index} but max is {max_steps_allowed} — overriding"
        )
        data["is_final_step"] = False
        data["final_answer"] = None
        is_final = False
        # If the model also omitted question (it thought it was finalising),
        # inject a safe fallback so Rule 4 doesn't fail a recoverable response
        if not question:
            data["question"] = "Can you walk me through your thinking so far?"
            question = data["question"]

    # Rule 4 — Question presence on non-final steps
    if not is_final and not question:
        logger.warning("question field missing on non-final step")
        return ResponseValidationResult(is_valid=False, failure_reason="MISSING_QUESTION")

    # Rule 5 — Explanation length
    if len(explanation) > MAX_EXPLANATION_LENGTH:
        logger.warning(f"Explanation too long ({len(explanation)} chars) — truncating")
        data["explanation"] = explanation[:MAX_EXPLANATION_LENGTH]

    return ResponseValidationResult(is_valid=True, parsed=data)
