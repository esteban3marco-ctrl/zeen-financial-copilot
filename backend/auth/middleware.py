"""JWT authentication middleware for Supabase tokens."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from backend.auth.models import AuthUser
from backend.config import Settings, get_settings
from risk_gates.schemas import UserRole

logger = logging.getLogger(__name__)

_DEMO_USER = AuthUser(
    user_id="demo-user",
    email="demo@staq.ai",
    user_role=UserRole.BASIC,
    demo_mode=True,
)


def _role_from_string(role_str: str | None) -> UserRole:
    if role_str is None:
        return UserRole.BASIC
    try:
        return UserRole(role_str.lower())
    except ValueError:
        return UserRole.BASIC


async def get_current_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthUser:
    """Extract and verify the Supabase JWT from the Authorization header."""
    authorization: str | None = request.headers.get("Authorization")

    token: str | None = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()

    if not token:
        if settings.DEMO_MODE:
            demo_role_header = request.headers.get("X-Demo-Role")
            user = _DEMO_USER.model_copy(
                update={"user_role": _role_from_string(demo_role_header)}
            )
            return user
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        from jose import JWTError, jwt as jose_jwt

        payload = jose_jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        user_id: str = payload.get("sub", "")
        email: str | None = payload.get("email")
        raw_role: str | None = (
            payload.get("user_role")
            or payload.get("app_metadata", {}).get("user_role")
        )
        user_role = _role_from_string(raw_role)

        user = AuthUser(
            user_id=user_id,
            email=email,
            user_role=user_role,
            demo_mode=settings.DEMO_MODE,
        )

        # In demo mode allow header to override role even for valid tokens
        if settings.DEMO_MODE:
            demo_role_header = request.headers.get("X-Demo-Role")
            if demo_role_header:
                user = user.model_copy(
                    update={"user_role": _role_from_string(demo_role_header)}
                )

        return user

    except ImportError:
        logger.warning("python-jose not installed — falling back to demo user")
        if settings.DEMO_MODE:
            return _DEMO_USER
        raise HTTPException(status_code=500, detail="JWT library not available")

    except Exception as exc:  # JWTError and everything else
        logger.warning("JWT validation failed: %s", exc)
        if settings.DEMO_MODE:
            demo_role_header = request.headers.get("X-Demo-Role")
            return _DEMO_USER.model_copy(
                update={"user_role": _role_from_string(demo_role_header)}
            )
        raise HTTPException(status_code=401, detail="Invalid authentication token")
