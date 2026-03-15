"""AgentState and all supporting data models for the LangGraph runtime."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field

from risk_gates.schemas import GateDecision, GateName, RiskContext, ToolCall


class ErrorSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class AgentError(BaseModel):
    code: str
    message: str
    severity: ErrorSeverity
    node: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    call_id: str
    tool_name: str
    status: Literal["success", "error", "timeout", "denied"]
    result: Any = None
    error_message: str | None = None
    execution_time_ms: float = 0.0
    sandbox_used: bool = False


class UserPreference(BaseModel):
    key: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class SessionMemory(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    context_window_messages: list[AnyMessage] = Field(default_factory=list)
    max_context_messages: int = Field(default=20)
    recent_tool_results: list[ToolResult] = Field(default_factory=list)
    detected_preferences: list[UserPreference] = Field(default_factory=list)
    session_start: datetime = Field(default_factory=datetime.utcnow)
    turn_count: int = 0


class TraceMetadata(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str | None = None
    parent_span_id: str | None = None
    model_used: str = ""
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    latency_ms: float = 0.0


class LLMInvokeInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    messages: list[AnyMessage]
    model: str = "claude-sonnet-4-6"
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=128_000)
    sanitized_input: str | None = None


class LLMInvokeOutput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ai_message: AnyMessage
    tool_calls: list[ToolCall] = Field(default_factory=list)
    model_used: str
    tokens_prompt: int = 0
    tokens_completion: int = 0
    finish_reason: str = "stop"


class CheckpointState(BaseModel):
    agent_state: dict[str, Any]
    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    iteration: int = 0
    is_resumable: bool = True
    message_index: int = 0


class AgentState(BaseModel):
    """Root state object flowing through every LangGraph node."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Core conversation — uses LangGraph add_messages reducer via Annotated
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    original_input: str = ""

    # Risk context (from Module 1)
    risk_context: RiskContext | None = None

    # Tool execution
    current_tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)

    # Gate decisions keyed by GateName value
    gate_decisions: dict[str, GateDecision] = Field(default_factory=dict)

    # Loop control
    iteration_count: int = Field(default=0, ge=0)
    max_iterations: int = Field(default=5, ge=1, le=10)

    # Memory
    session_memory: SessionMemory = Field(default_factory=SessionMemory)

    # Observability
    metadata: TraceMetadata = Field(default_factory=TraceMetadata)

    # Error
    error: AgentError | None = None

    # Routing hints consumed by conditional edges
    next_action: Literal[
        "continue", "route_tools", "respond", "error", "loop_back"
    ] = "continue"
