import hmac
import logging
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()
_jwks_cache: Optional[dict] = None

# ── Dev bypass ────────────────────────────────────────────────────────────────
# The accepted token comes from settings.dev_bypass_token (DEV_BYPASS_TOKEN in
# .env), never hardcoded here — see settings.py for why.
DEV_STUDENT_ID = "dev-student-001"

class AuthenticatedStudent:
    def __init__(self, student_id: str, claims: dict):
        self.student_id = student_id
        self.claims = claims

def _cognito_jwks_url() -> str:
    s = get_settings()
    return (f"https://cognito-idp.{s.cognito_region}.amazonaws.com"
            f"/{s.cognito_user_pool_id}/.well-known/jwks.json")


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(_cognito_jwks_url(), timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        logger.info("Cognito JWKS loaded and cached.")
    return _jwks_cache


def _get_public_key(token: str, jwks: dict):
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    for key in jwks.get("keys", []):
        if key["kid"] == kid:
            return jwk.construct(key)
    return None


async def validate_cognito_token(token: str) -> dict:
    try:
        jwks = await _get_jwks()
        public_key = _get_public_key(token, jwks)
        if public_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token signing key not found."
            )
        claims = jwt.decode(
            token, public_key,
            algorithms=["RS256"],
            options={"verify_at_hash": False}
        )
        return claims
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch Cognito JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable."
        )


async def get_current_student(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthenticatedStudent:
    settings = get_settings()
    token = credentials.credentials

    # ── Dev bypass ────────────────────────────────────────────────────────────
    # In development, accept the configured dev token without hitting Cognito.
    # dev_bypass_token defaults to "" (disabled) so this never matches unless
    # a deployment has explicitly set one.
    if (
        settings.environment == "development"
        and settings.dev_bypass_token
        and hmac.compare_digest(token, settings.dev_bypass_token)
    ):
        logger.debug("Dev token accepted — bypassing Cognito validation")
        return AuthenticatedStudent(
            student_id=DEV_STUDENT_ID,
            claims={"sub": DEV_STUDENT_ID, "dev": True}
        )

    # ── Production: real Cognito validation ───────────────────────────────────
    claims = await validate_cognito_token(token)
    student_id = claims.get(settings.student_id_field)
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token missing field: {settings.student_id_field}"
        )
    return AuthenticatedStudent(student_id=student_id, claims=claims)
