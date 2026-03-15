from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class GateAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    MODIFY = "modify"


class GateName(str, Enum):
    PRE_LLM = "pre_llm"
    POST_LLM = "post_llm"
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"


class UserRole(str, Enum):
    ANONYMOUS = "anonymous"
    BASIC = "basic"
    PREMIUM = "premium"
    ADVISOR = "advisor"
    ADMIN = "admin"


class RiskContext(BaseModel):
    """Immutable risk context shared across all gates in a single request."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str
    user_role: UserRole
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    requests_in_window: int = Field(default=0, ge=0)
    tools_called_in_window: int = Field(default=0, ge=0)
    window_seconds: int = Field(default=60)
    authorized_topics: list[str] = Field(
        default_factory=lambda: [
            "budgeting", "expense_tracking", "general_finance",
            "market_data", "portfolio_view",
        ]
    )
    compliance_jurisdiction: str = Field(default="US")
    trace_id: str | None = None
    span_id: str | None = None


class AuditEntry(BaseModel):
    gate: GateName
    action: GateAction
    reason: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: str
    user_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GateDecision(BaseModel):
    action: GateAction
    reason: str
    audit: AuditEntry

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Gate decision reason must not be empty")
        return v


class PIIMatch(BaseModel):
    pii_type: str
    start_index: int
    end_index: int
    redacted_value: str


class PreLLMRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=32_000)
    risk_context: RiskContext


class PreLLMDecision(BaseModel):
    gate_decision: GateDecision
    sanitized_input: str | None = None
    detected_pii: list[PIIMatch] = Field(default_factory=list)
    injection_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ToolCall(BaseModel):
    tool_name: str
    tool_params: dict[str, Any] = Field(default_factory=dict)
    call_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class HallucinationMarker(BaseModel):
    text_span: str
    marker_type: str
    confidence: float = Field(ge=0.0, le=1.0)


class PostLLMRequest(BaseModel):
    llm_response: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    risk_context: RiskContext
    original_input: str


class PostLLMDecision(BaseModel):
    gate_decision: GateDecision
    modified_response: str | None = None
    compliance_flags: list[str] = Field(default_factory=list)
    hallucination_markers: list[HallucinationMarker] = Field(default_factory=list)


class PreToolRequest(BaseModel):
    tool_name: str
    tool_params: dict[str, Any] = Field(default_factory=dict)
    risk_context: RiskContext


class PreToolDecision(BaseModel):
    gate_decision: GateDecision
    requires_sandbox: bool = False
    rate_limit_remaining: int = Field(default=-1)
    sanitized_params: dict[str, Any] | None = None


class PostToolRequest(BaseModel):
    tool_name: str
    tool_result: Any
    execution_time_ms: float = Field(ge=0.0)
    risk_context: RiskContext


class PostToolDecision(BaseModel):
    gate_decision: GateDecision
    sanitized_result: Any | None = None
    secrets_found: list[str] = Field(default_factory=list)
    data_freshness: str | None = None
