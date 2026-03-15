"""Pydantic models for Supabase-persisted memory rows."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from risk_gates.schemas import UserRole


class MessageRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Literal["human", "ai", "tool", "system"]
    content: str
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_params: dict[str, Any] | None = None
    embedding: list[float] | None = None
    gate_decisions: dict[str, Any] | None = None
    tokens_used: int = 0
    sequence_num: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationMemory(BaseModel):
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str
    messages: list[MessageRecord] = Field(default_factory=list)
    title: str | None = None
    turn_count: int = 0
    total_tokens: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    status: Literal["active", "completed", "error", "expired"] = "active"


class UserProfile(BaseModel):
    user_id: str
    display_name: str | None = None
    role: UserRole = UserRole.BASIC
    compliance_jurisdiction: str = "US"
    portfolio_size_tier: str | None = None
    risk_tolerance: str | None = None
    authorized_topics: list[str] = Field(
        default_factory=lambda: [
            "budgeting", "expense_tracking", "general_finance",
            "market_data", "portfolio_view",
        ]
    )
    preferences: dict[str, Any] = Field(default_factory=dict)
    total_sessions: int = 0
    total_messages: int = 0
    last_active_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
