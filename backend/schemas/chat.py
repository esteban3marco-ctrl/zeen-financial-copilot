"""Chat request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from risk_gates.schemas import UserRole


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=32_000)
    session_id: str | None = None
    user_role: UserRole = UserRole.BASIC


class MessageOut(BaseModel):
    role: Literal["ai", "error"]
    content: str
    turn_index: int
    created_at: datetime


class TurnMetadataOut(BaseModel):
    trace_id: str
    model_used: str
    tokens_prompt: int
    tokens_completion: int
    latency_ms: float
    iteration_count: int


class ChatResponse(BaseModel):
    session_id: str
    request_id: str
    message: MessageOut
    gate_events: list[Any]  # list[GateEventOut] — avoids circular import
    tool_events: list[Any]  # list[ToolEventOut]
    metadata: TurnMetadataOut
    blocked: bool
