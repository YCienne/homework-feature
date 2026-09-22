import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.api.middleware.auth import get_current_student, DEV_STUDENT_ID


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class _FakeSettings:
    def __init__(self, environment="development", dev_bypass_token="", student_id_field="sub"):
        self.environment = environment
        self.dev_bypass_token = dev_bypass_token
        self.student_id_field = student_id_field


@pytest.mark.asyncio
async def test_dev_bypass_disabled_by_default():
    """An empty dev_bypass_token (the default) must never match any token."""
    settings = _FakeSettings(dev_bypass_token="")
    with patch("src.api.middleware.auth.get_settings", return_value=settings), \
         patch("src.api.middleware.auth.validate_cognito_token", new=AsyncMock(side_effect=HTTPException(401))):
        with pytest.raises(HTTPException) as exc:
            await get_current_student(_creds(""))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_dev_bypass_accepts_the_configured_token():
    settings = _FakeSettings(dev_bypass_token="s3cret-demo-token")
    with patch("src.api.middleware.auth.get_settings", return_value=settings):
        student = await get_current_student(_creds("s3cret-demo-token"))
    assert student.student_id == DEV_STUDENT_ID


@pytest.mark.asyncio
async def test_dev_bypass_rejects_wrong_token():
    settings = _FakeSettings(dev_bypass_token="s3cret-demo-token")
    with patch("src.api.middleware.auth.get_settings", return_value=settings), \
         patch("src.api.middleware.auth.validate_cognito_token", new=AsyncMock(side_effect=HTTPException(401))):
        with pytest.raises(HTTPException):
            await get_current_student(_creds("wrong-token"))


@pytest.mark.asyncio
async def test_dev_bypass_does_not_apply_outside_development():
    """Even a correct dev token must not bypass auth in production."""
    settings = _FakeSettings(environment="production", dev_bypass_token="s3cret-demo-token")
    with patch("src.api.middleware.auth.get_settings", return_value=settings), \
         patch("src.api.middleware.auth.validate_cognito_token", new=AsyncMock(side_effect=HTTPException(401))) as mock_validate:
        with pytest.raises(HTTPException):
            await get_current_student(_creds("s3cret-demo-token"))
    mock_validate.assert_awaited_once()
