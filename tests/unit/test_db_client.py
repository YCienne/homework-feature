import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.store import db_client
from src.store.db_client import LazyDBSession, get_db_session


@pytest.mark.asyncio
async def test_get_db_session_does_not_touch_the_database_until_used():
    """Regression: resolving the dependency used to build the engine on every action request."""
    with patch.object(db_client, "get_session_factory", side_effect=AssertionError("engine built eagerly")):
        gen = get_db_session()
        db = await gen.__anext__()
        assert isinstance(db, LazyDBSession)
        await db.commit()      # no-ops when nothing was opened
        await db.rollback()
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()


@pytest.mark.asyncio
async def test_lazy_session_opens_once_and_delegates():
    real = MagicMock()
    real.execute = AsyncMock(return_value="result")
    real.commit = AsyncMock()
    real.rollback = AsyncMock()
    real.close = AsyncMock()
    factory = MagicMock(return_value=real)

    with patch.object(db_client, "get_session_factory", return_value=factory):
        db = LazyDBSession()
        assert await db.execute("SELECT 1") == "result"
        await db.execute("SELECT 2")
        await db.commit()
        await db.rollback()
        await db.close()

    factory.assert_called_once()           # one real session, reused
    real.commit.assert_awaited_once()
    real.rollback.assert_awaited_once()
    real.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_lazy_session_surfaces_connection_errors_on_first_use():
    """record_concept relies on this raising inside its try/except so tracking failures are swallowed."""
    with patch.object(db_client, "get_session_factory", side_effect=RuntimeError("no db configured")):
        db = LazyDBSession()
        with pytest.raises(RuntimeError):
            await db.execute("SELECT 1")
        await db.rollback()    # must stay safe after a failed open
