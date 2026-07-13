import logging
from typing import Optional

import redis.asyncio as aioredis

from src.config.settings import get_settings
from src.core.session.session_schema import Session, StepRecord

logger = logging.getLogger(__name__)

SESSION_KEY_PREFIX = "hw:session:"
USAGE_KEY_PREFIX = "hw:usage:"


def _session_key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


def _usage_key(student_id: str) -> str:
    return f"{USAGE_KEY_PREFIX}{student_id}"


class SessionManager:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis
        self.settings = get_settings()

    async def create(self, session: Session) -> Session:
        key = _session_key(session.session_id)
        await self.redis.setex(key, self.settings.session_ttl_seconds, session.to_redis())
        logger.info(f"Session created: {session.session_id} | student: {session.student_id}")
        return session

    async def get(self, session_id: str) -> Optional[Session]:
        data = await self.redis.get(_session_key(session_id))
        if not data:
            return None
        return Session.from_redis(data)

    async def save(self, session: Session) -> Session:
        session.mark_updated()
        await self.redis.setex(
            _session_key(session.session_id),
            self.settings.session_ttl_seconds,
            session.to_redis(),
        )
        return session

    async def advance_step(self, session: Session, step_question: str, student_response: str | None = None) -> Session:
        """Advance step index and record the step in history."""
        record = StepRecord(
            step_index=session.current_step_index,
            step_question=step_question,
            student_response=student_response,
        )
        session.step_history.append(record)
        session.current_step_index += 1
        session.steps_revealed += 1
        session.skip_attempts = 0
        return await self.save(session)

    async def record_skip_attempt(self, session: Session) -> Session:
        session.skip_attempts += 1
        return await self.save(session)

    async def record_hint_used(self, session: Session) -> Session:
        session.hints_used += 1
        return await self.save(session)

    async def complete_session(self, session: Session) -> Session:
        session.is_complete = True
        return await self.save(session)

    async def get_daily_usage(self, student_id: str) -> int:
        count = await self.redis.get(_usage_key(student_id))
        return int(count) if count else 0

    async def increment_daily_usage(self, student_id: str) -> int:
        key = _usage_key(student_id)
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 86400)
        return count

    async def check_daily_limit(self, student_id: str) -> tuple[bool, int, int]:
        limit = self.settings.daily_session_limit
        used = await self.get_daily_usage(student_id)
        return used < limit, used, max(0, limit - used)

    def verify_ownership(self, session: Session, student_id: str) -> bool:
        return session.student_id == student_id
