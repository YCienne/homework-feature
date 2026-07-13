import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_MEANINGFUL_PATTERN = re.compile(r"[a-zA-Z]{3,}")
_HTML_PATTERN = re.compile(r"<[^>]+>")
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"disregard\s+(your\s+)?(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
]

MAX_INPUT_LENGTH = 2000
MIN_INPUT_LENGTH = 5


@dataclass
class ValidationResult:
    is_valid: bool
    clean_text: str = ""
    error_code: str = ""
    error_message: str = ""


def validate_question(raw_input: str) -> ValidationResult:
    if not raw_input or not raw_input.strip():
        return ValidationResult(is_valid=False, error_code="INVALID_INPUT",
            error_message="I couldn't understand the question. Please type or rephrase it clearly.")

    text = _HTML_PATTERN.sub("", raw_input.strip())

    if len(text) < MIN_INPUT_LENGTH:
        return ValidationResult(is_valid=False, error_code="INVALID_INPUT",
            error_message="I couldn't understand the question. Please type or rephrase it clearly.")

    if len(text) > MAX_INPUT_LENGTH:
        return ValidationResult(is_valid=False, error_code="INPUT_TOO_LONG",
            error_message=f"Please keep your question under {MAX_INPUT_LENGTH} characters.")

    if not _MEANINGFUL_PATTERN.search(text):
        return ValidationResult(is_valid=False, error_code="INVALID_INPUT",
            error_message="I couldn't understand the question. Please type or rephrase it clearly.")

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning(f"Prompt injection attempt: {text[:80]}")
            return ValidationResult(is_valid=False, error_code="INVALID_INPUT",
                error_message="I couldn't understand the question. Please type or rephrase it clearly.")

    return ValidationResult(is_valid=True, clean_text=" ".join(text.split()))
