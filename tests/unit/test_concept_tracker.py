"""
Unit tests for concept tracker.
Uses AsyncMock for the DB session — tracking must never raise.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.tracking.concept_tracker import (
    record_concept,
    get_student_concepts,
    get_weak_areas,
    _calculate_struggle_index,
)


# ── Struggle index ────────────────────────────────────────────────────────────

def test_struggle_index_zero():
    assert _calculate_struggle_index(0, 0, 5) == 0.0

def test_struggle_index_some_hints():
    assert _calculate_struggle_index(2, 1, 3) == 1.0  # (2+1)/3

def test_struggle_index_zero_steps_no_division_error():
    # steps_needed=0 uses max(0,1)=1 as denominator
    assert _calculate_struggle_index(2, 1, 0) == 3.0


# ── record_concept ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_record_concept_success(mock_db):
    await record_concept(
        db=mock_db,
        student_id="s-1",
        session_id="sess-1",
        subject="math",
        topic="fractions",
        completed=True,
        steps_needed=4,
        hints_used=1,
        skips_used=0,
    )
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_record_concept_db_failure_does_not_raise(mock_db):
    """DB failure must never propagate to the student response."""
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection lost"))
    # Should complete without raising
    await record_concept(
        db=mock_db,
        student_id="s-1",
        session_id="sess-1",
        subject="math",
        topic="fractions",
        completed=True,
        steps_needed=3,
        hints_used=0,
        skips_used=0,
    )
    mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_record_concept_incomplete_session(mock_db):
    await record_concept(
        db=mock_db,
        student_id="s-1",
        session_id="sess-2",
        subject="science",
        topic="photosynthesis",
        completed=False,
        steps_needed=2,
        hints_used=3,
        skips_used=2,
    )
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()
    # Verify struggle_index was high
    call_kwargs = mock_db.execute.call_args[0][1]
    assert call_kwargs["struggle_index"] > 1.0


# ── get_student_concepts ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_student_concepts_success(mock_db):
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [
        {"subject": "math", "topic": "fractions", "completed": True,
         "steps_needed": 4, "hints_used": 1, "skips_used": 0,
         "struggle_index": 0.25, "created_at": "2025-01-01"},
    ]
    mock_db.execute = AsyncMock(return_value=mock_result)
    result = await get_student_concepts(mock_db, "s-1")
    assert len(result) == 1
    assert result[0]["subject"] == "math"


@pytest.mark.asyncio
async def test_get_student_concepts_db_failure_returns_empty(mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB down"))
    result = await get_student_concepts(mock_db, "s-1")
    assert result == []


# ── get_weak_areas ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_weak_areas_success(mock_db):
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [
        {"subject": "math", "topic": "algebra",
         "avg_struggle": 1.8, "attempts": 3, "completions": 1},
    ]
    mock_db.execute = AsyncMock(return_value=mock_result)
    result = await get_weak_areas(mock_db, "s-1", threshold=1.0)
    assert len(result) == 1
    assert result[0]["topic"] == "algebra"


@pytest.mark.asyncio
async def test_get_weak_areas_db_failure_returns_empty(mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB down"))
    result = await get_weak_areas(mock_db, "s-1")
    assert result == []
