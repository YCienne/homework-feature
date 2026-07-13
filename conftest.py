"""
conftest.py — shared pytest fixtures and configuration.
Place this file in the homework-service/ root (same level as pytest.ini).

Run tests from the homework-service/ directory:
    cd homework-service
    pytest
"""
import asyncio
import sys
import pytest
from unittest.mock import AsyncMock


# ── Windows: fix "Event loop is closed" with ProactorEventLoop ────────────────
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ── Shared mock student (imported lazily to avoid circular import at collection)
def _make_mock_student():
    from src.api.middleware.auth import AuthenticatedStudent
    return AuthenticatedStudent(
        student_id="student-test-123",
        claims={"sub": "student-test-123"},
    )


# ── Mock Redis factory ─────────────────────────────────────────────────────────
def _make_mock_redis():
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def mock_redis_client():
    """Standalone mock Redis — use in unit tests that need Redis directly."""
    return _make_mock_redis()


@pytest.fixture(autouse=True)
def override_app_dependencies():
    """
    Overrides FastAPI dependencies for EVERY test automatically.
    Replaces: Cognito auth, rate limiter, and Redis client.

    Also provides a silent default DB mock so routes that use get_db_session
    don't fail with a real DB connection attempt.

    Yields the mock Redis so individual tests can configure .get() etc:
        def test_foo(override_app_dependencies):
            override_app_dependencies.get = AsyncMock(return_value=session.to_redis())
    """
    from main import app
    from src.api.middleware.auth import get_current_student
    from src.api.middleware.rate_limit import check_rate_limit
    from src.store.redis_client import get_redis
    from src.store.db_client import get_db_session

    mock_student = _make_mock_student()
    mock_redis = _make_mock_redis()

    # Silent default DB — execute/commit/rollback all succeed
    # Tests that need to assert on DB calls should use the mock_db fixture
    # in test_concept_tracking.py which re-registers its own instance
    _default_db = AsyncMock()
    _default_db.execute = AsyncMock()
    _default_db.commit = AsyncMock()
    _default_db.rollback = AsyncMock()

    async def _student():
        return mock_student

    async def _redis():
        return mock_redis

    async def _db():
        yield _default_db

    app.dependency_overrides[get_current_student] = _student
    app.dependency_overrides[check_rate_limit] = _student
    app.dependency_overrides[get_redis] = _redis
    app.dependency_overrides[get_db_session] = _db

    yield mock_redis

    app.dependency_overrides.clear()
