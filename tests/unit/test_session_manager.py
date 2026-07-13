import pytest
from unittest.mock import AsyncMock
from src.core.session.session_manager import SessionManager
from src.core.session.session_schema import Session


def make_session(**kw) -> Session:
    defaults = dict(
        student_id="s-123",
        question_raw="test?",
        question_clean="test?",
        subject="math",
        topic="fractions",
        max_steps_allowed=5,
    )
    defaults.update(kw)   # caller overrides win — no duplicate keyword error
    return Session(**defaults)


@pytest.fixture
def redis():
    r = AsyncMock()
    r.setex = AsyncMock(return_value=True)
    r.get = AsyncMock(return_value=None)
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock(return_value=True)
    return r


@pytest.mark.asyncio
async def test_create(redis):
    m = SessionManager(redis)
    s = make_session()
    await m.create(s)
    redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_get_not_found(redis):
    assert await SessionManager(redis).get("bad-id") is None


@pytest.mark.asyncio
async def test_get_found(redis):
    s = make_session()
    redis.get = AsyncMock(return_value=s.to_redis())
    result = await SessionManager(redis).get(s.session_id)
    assert result.session_id == s.session_id


@pytest.mark.asyncio
async def test_advance_step(redis):
    s = make_session()
    result = await SessionManager(redis).advance_step(s, "What do you know?", "Something")
    assert result.current_step_index == 1
    assert result.steps_revealed == 1
    assert result.skip_attempts == 0
    assert len(result.step_history) == 1


@pytest.mark.asyncio
async def test_skip_attempts(redis):
    s = make_session()
    result = await SessionManager(redis).record_skip_attempt(s)
    assert result.skip_attempts == 1


@pytest.mark.asyncio
async def test_complete(redis):
    s = make_session()
    result = await SessionManager(redis).complete_session(s)
    assert result.is_complete is True


@pytest.mark.asyncio
async def test_limit_not_reached(redis):
    redis.get = AsyncMock(return_value="3")
    within, used, remaining = await SessionManager(redis).check_daily_limit("s-123")
    assert within is True and used == 3 and remaining == 2


@pytest.mark.asyncio
async def test_limit_reached(redis):
    redis.get = AsyncMock(return_value="5")
    within, used, remaining = await SessionManager(redis).check_daily_limit("s-123")
    assert within is False and remaining == 0


def test_ownership_pass(): assert SessionManager(AsyncMock()).verify_ownership(make_session(student_id="abc"), "abc")
def test_ownership_fail(): assert not SessionManager(AsyncMock()).verify_ownership(make_session(student_id="abc"), "xyz")
