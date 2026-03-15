"""Authentication user model."""
from __future__ import annotations

from pydantic import BaseModel

from risk_gates.schemas import UserRole


class AuthUser(BaseModel):
    user_id: str
    email: str | None = None
    user_role: UserRole = UserRole.BASIC
    demo_mode: bool = False
