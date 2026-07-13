"""
Integration tests for image upload and extraction flow.
Auth, rate limit, and Redis are overridden via conftest.py fixtures.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from main import app


VALID_IMAGE = b"\xff\xd8\xff" + b"x" * 5000  # Minimal valid JPEG size


@pytest.fixture
def mock_llm():
    response = json.dumps({
        "step_title": "Step 1", "explanation": "Let's start.",
        "question": "What do you know about triangles?", "hint": None,
        "final_answer": None, "is_final_step": False,
    })
    with patch("src.core.llm.retry_handler.call_llm", new=AsyncMock(return_value=response)):
        yield


# ── Image extract endpoint ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_image_extract_success():
    extracted = "What is the area of a rectangle with width 4cm and height 6cm?"
    with patch("src.core.image.image_extractor.call_vision", new=AsyncMock(return_value=extracted)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/homework/image/extract",
                files={"image": ("test.jpg", VALID_IMAGE, "image/jpeg")},
                headers={"Authorization": "Bearer fake"},
            )
    assert r.status_code == 200
    data = r.json()
    assert "extraction_id" in data
    assert data["extracted_text"] == extracted
    assert data["confidence"] in ("high", "medium")


@pytest.mark.asyncio
async def test_image_extract_invalid_type():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/homework/image/extract",
            files={"image": ("test.gif", b"GIF89a" + b"x" * 5000, "image/gif")},
            headers={"Authorization": "Bearer fake"},
        )
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "INVALID_IMAGE_TYPE"


@pytest.mark.asyncio
async def test_image_extract_too_large():
    large_image = b"x" * (6 * 1024 * 1024)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/homework/image/extract",
            files={"image": ("big.jpg", large_image, "image/jpeg")},
            headers={"Authorization": "Bearer fake"},
        )
    assert r.status_code == 413
    assert r.json()["detail"]["error"] == "IMAGE_TOO_LARGE"


@pytest.mark.asyncio
async def test_image_extract_unreadable():
    with patch("src.core.image.image_extractor.call_vision", new=AsyncMock(return_value="")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/homework/image/extract",
                files={"image": ("blur.jpg", VALID_IMAGE, "image/jpeg")},
                headers={"Authorization": "Bearer fake"},
            )
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "IMAGE_UNREADABLE"


# ── Image flow → session/start ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_start_with_valid_extraction_id(override_app_dependencies, mock_llm):
    stored_text = "What is the area of a triangle with base 5 and height 3?"
    override_app_dependencies.get = AsyncMock(return_value=stored_text)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/homework/session/start",
            json={
                "student_id": "student-test-123",
                "question": stored_text,
                "extraction_id": "valid-extraction-id",
            },
            headers={"Authorization": "Bearer fake"},
        )
    assert r.status_code == 200
    assert "session_id" in r.json()


@pytest.mark.asyncio
async def test_session_start_with_expired_extraction_id(override_app_dependencies):
    override_app_dependencies.get = AsyncMock(return_value=None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/homework/session/start",
            json={
                "student_id": "student-test-123",
                "question": "What is gravity?",
                "extraction_id": "expired-id",
            },
            headers={"Authorization": "Bearer fake"},
        )
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "EXTRACTION_EXPIRED"
