import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, Field
from src.config.settings import get_settings


class StepRecord(BaseModel):
    step_index: int
    step_question: str
    student_response: Optional[str] = None


class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    question_raw: str
    question_clean: str
    subject: str = "general"
    topic: str = "general"
    current_step_index: int = 0
    max_steps_allowed: int = 5
    steps_revealed: int = 0
    skip_attempts: int = 0
    hints_used: int = 0
    is_complete: bool = False
    step_history: list[StepRecord] = Field(default_factory=list)
    last_step_question: str = ""
    last_step_explanation: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = Field(default_factory=lambda: _default_expiry())

    def mark_updated(self):
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_redis(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_redis(cls, data: str) -> "Session":
        return cls.model_validate_json(data)


class SessionCreate(BaseModel):
    student_id: str
    question: str
    platform: Optional[str] = None
    lesson_subject: Optional[str] = None
    lesson_topic: Optional[str] = None
    grade_level: Optional[str] = None
    extraction_id: Optional[str] = None


class ActionRequest(BaseModel):
    action: str
    response: Optional[str] = None


class StepResponse(BaseModel):
    session_id: str
    step_title: str
    explanation: str
    question: Optional[str] = None
    hint: Optional[str] = None
    final_answer: Optional[str] = None
    is_final_step: bool = False


def _default_expiry() -> str:
    settings = get_settings()
    return (datetime.now(timezone.utc) + timedelta(seconds=settings.session_ttl_seconds)).isoformat()
