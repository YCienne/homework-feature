import logging
from datetime import datetime, timezone, timedelta

from fastapi import Depends, HTTPException, status

from src.api.middleware.auth import AuthenticatedStudent, get_current_student
from src.core.session.session_manager import SessionManager
from src.store.redis_client import get_redis

logger = logging.getLogger(__name__)


async def check_rate_limit(
    student: AuthenticatedStudent = Depends(get_current_student),
    redis=Depends(get_redis),
) -> AuthenticatedStudent:
    manager = SessionManager(redis)
    within_limit, used, remaining = await manager.check_daily_limit(student.student_id)
    if not within_limit:
        from src.config.settings import get_settings
        settings = get_settings()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "DAILY_LIMIT_REACHED",
                "message": "You've used all your homework help sessions for today. Come back tomorrow!",
                "sessions_used": used,
                "sessions_limit": settings.daily_session_limit,
                "resets_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            },
        )
    return student
