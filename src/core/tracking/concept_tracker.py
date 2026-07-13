"""
Concept Tracker — Phase 4
Writes a concept tag to MySQL after every completed session.
Fire-and-forget: tracking failure must never break the student experience.
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


def _calculate_struggle_index(hints_used: int, skips_used: int, steps_needed: int) -> float:
    """
    Struggle index: ratio of help-seeking behaviour to steps taken.
    Range: 0.0 (no help needed) to unbounded (many hints on few steps).
    Used for weak area detection in the teacher dashboard (future).
    """
    return round((hints_used + skips_used) / max(steps_needed, 1), 2)


async def record_concept(
    db: AsyncSession,
    student_id: str,
    session_id: str,
    subject: str,
    topic: str,
    completed: bool,
    steps_needed: int,
    hints_used: int,
    skips_used: int,
) -> None:
    """
    Writes a concept tracking record to the concept_tags table.

    Fails silently — a tracking write failure must never surface to the student.
    On failure, logs the error for monitoring alerting to catch.

    Args:
        db:           Async SQLAlchemy session
        student_id:   From session object
        session_id:   UUID of the completed session
        subject:      e.g. "math"
        topic:        e.g. "fractions"
        completed:    True if student reached is_final_step
        steps_needed: How many steps the student required
        hints_used:   Number of IM_NOT_SURE presses
        skips_used:   Number of SHOW_NEXT_STEP presses
    """
    try:
        struggle_index = _calculate_struggle_index(hints_used, skips_used, steps_needed)
        tag_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        await db.execute(
            text("""
                INSERT INTO concept_tags
                    (id, student_id, session_id, subject, topic, completed,
                     steps_needed, hints_used, skips_used, struggle_index, created_at)
                VALUES
                    (:id, :student_id, :session_id, :subject, :topic, :completed,
                     :steps_needed, :hints_used, :skips_used, :struggle_index, :created_at)
            """),
            {
                "id": tag_id,
                "student_id": student_id,
                "session_id": session_id,
                "subject": subject,
                "topic": topic,
                "completed": completed,
                "steps_needed": steps_needed,
                "hints_used": hints_used,
                "skips_used": skips_used,
                "struggle_index": struggle_index,
                "created_at": now,
            },
        )
        await db.commit()

        logger.info(
            f"Concept tag recorded: student={student_id} "
            f"subject={subject} topic={topic} "
            f"completed={completed} struggle_index={struggle_index}"
        )

    except Exception as e:
        # Never raise — tracking failure must not affect the student response
        logger.error(
            f"Failed to record concept tag for session {session_id}: {e}",
            exc_info=True,
        )
        try:
            await db.rollback()
        except Exception:
            pass


async def get_student_concepts(
    db: AsyncSession,
    student_id: str,
    limit: int = 50,
) -> list[dict]:
    """
    Returns recent concept tags for a student.
    Used by: teacher dashboard, progress tracking (future feature).
    """
    try:
        result = await db.execute(
            text("""
                SELECT subject, topic, completed, steps_needed,
                       hints_used, skips_used, struggle_index, created_at
                FROM concept_tags
                WHERE student_id = :student_id
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"student_id": student_id, "limit": limit},
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch concepts for student {student_id}: {e}")
        return []


async def get_weak_areas(
    db: AsyncSession,
    student_id: str,
    threshold: float = 1.0,
) -> list[dict]:
    """
    Returns subjects/topics where the student's average struggle_index
    exceeds the threshold. Used for weak area detection.
    threshold=1.0 means on average more than 1 hint/skip per step.
    """
    try:
        result = await db.execute(
            text("""
                SELECT subject, topic,
                       AVG(struggle_index) as avg_struggle,
                       COUNT(*) as attempts,
                       SUM(CASE WHEN completed THEN 1 ELSE 0 END) as completions
                FROM concept_tags
                WHERE student_id = :student_id
                GROUP BY subject, topic
                HAVING AVG(struggle_index) >= :threshold
                ORDER BY avg_struggle DESC
            """),
            {"student_id": student_id, "threshold": threshold},
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch weak areas for student {student_id}: {e}")
        return []
