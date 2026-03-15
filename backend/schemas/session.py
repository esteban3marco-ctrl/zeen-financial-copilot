"""Session schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessionOut(BaseModel):
    session_id: str
    user_id: str
    turn_count: int
    total_tokens: int
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SessionListResponse(BaseModel):
    sessions: list[SessionOut]
    total: int
