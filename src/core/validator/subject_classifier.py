import logging
from src.config.subjects import SUBJECTS, SubjectConfig

logger = logging.getLogger(__name__)


def classify_subject(text: str) -> tuple[str, SubjectConfig]:
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for subject, config in SUBJECTS.items():
        if subject == "general":
            continue
        score = sum(1 for kw in config.keywords if kw in text_lower)
        if score > 0:
            scores[subject] = score
    if not scores:
        return "general", SUBJECTS["general"]
    best = max(scores, key=lambda s: scores[s])
    logger.debug(f"Subject classified as '{best}' (score: {scores[best]})")
    return best, SUBJECTS[best]
