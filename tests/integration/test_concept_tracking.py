"""
Integration test: session completion triggers concept tracking.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from main import app
from src.core.session.session_schema import Session
from src.store.db_client import get_db_session


@pytest.fixture
def mock_db(override_app_dependencies):
    """
    Provides a named DB mock that tests can assert on.
    Depends on override_app_dependencies to guarantee it runs AFTER
    the base fixtures are set up, then overwrites the DB override
    with a traceable instance.

    override_app_dependencies is the conftest autouse fixture —
    explicitly requesting it here ensures correct fixture ordering.
    """
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    async def _db():
        yield db

    # Overwrite the silent default DB with our assertable instance
    app.dependency_overrides[get_db_session] = _db

    yield db
    # conftest teardown handles dependency_overrides.clear()


@pytest.mark.asyncio
async def test_concept_tag_written_on_session_complete(mock_db, override_app_dependencies):
    """
    When CONTINUE on the last step returns is_final_step=True,
    a concept tag must be written to the DB.
    """
    final_response = json.dumps({
        "step_title": "Well done!",
        "explanation": "Great work!",
        "question": None,
        "hint": None,
        "final_answer": "The answer is 10.",
        "is_final_step": True,
    })

    # Session at step 4 of 5 — the last step
    session = Session(
        student_id="student-test-123",
        question_raw="What is gravity?",
        question_clean="What is gravity?",
        subject="science",
        topic="forces",
        current_step_index=4,
        max_steps_allowed=5,
        hints_used=1,
        skip_attempts=0,
        last_step_question="What is the formula for gravitational force?",
    )
    override_app_dependencies.get = AsyncMock(return_value=session.to_redis())

    with patch("src.core.llm.retry_handler.call_llm", new=AsyncMock(return_value=final_response)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"/homework/session/{session.session_id}/action",
                json={"action": "CONTINUE", "response": "F = Gm1m2/r^2"},
                headers={"Authorization": "Bearer fake"},
            )

    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["is_final_step"] is True, f"Expected is_final_step=True, got: {data}"
    assert data["final_answer"] == "The answer is 10."
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_concept_tag_not_written_on_incomplete_step(mock_db, override_app_dependencies):
    """Mid-session CONTINUE must not write a concept tag."""
    mid_response = json.dumps({
        "step_title": "Step 2",
        "explanation": "Good progress.",
        "question": "What happens next?",
        "hint": None,
        "final_answer": None,
        "is_final_step": False,
    })

    session = Session(
        student_id="student-test-123",
        question_raw="What is gravity?",
        question_clean="What is gravity?",
        subject="science",
        topic="forces",
        current_step_index=1,
        max_steps_allowed=5,
        last_step_question="What is gravity?",
    )
    override_app_dependencies.get = AsyncMock(return_value=session.to_redis())

    with patch("src.core.llm.retry_handler.call_llm", new=AsyncMock(return_value=mid_response)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"/homework/session/{session.session_id}/action",
                json={"action": "CONTINUE", "response": "Gravity pulls things down"},
                headers={"Authorization": "Bearer fake"},
            )

    assert r.status_code == 200
    assert r.json()["is_final_step"] is False
    mock_db.execute.assert_not_called()
