"""
SQLAlchemy models for Phase 4 concept tracking.
Table: concept_tags — one row per completed homework session.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from src.store.db_client import Base


class ConceptTag(Base):
    __tablename__ = "concept_tags"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    student_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    subject: Mapped[str] = mapped_column(String(64), nullable=False)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    steps_needed: Mapped[int] = mapped_column(Integer, default=0)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    skips_used: Mapped[int] = mapped_column(Integer, default=0)

    # Derived struggle index: higher = more difficulty
    # Calculated as: (hints_used + skips_used) / max(steps_needed, 1)
    struggle_index: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<ConceptTag student={self.student_id} "
            f"subject={self.subject} topic={self.topic} "
            f"completed={self.completed}>"
        )
