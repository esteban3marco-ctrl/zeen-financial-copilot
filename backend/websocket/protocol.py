"""WebSocket message protocol — all server→client message types."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


class WSConnected(BaseModel):
    type: Literal["connected"] = "connected"
    session_id: str
    server_time: datetime = Field(default_factory=datetime.utcnow)


class WSTurnStart(BaseModel):
    type: Literal["turn_start"] = "turn_start"
    request_id: str
    session_id: str
    turn_id: str = ""  # alias for request_id — populated by model_post_init

    def model_post_init(self, __context: Any) -> None:
        if not self.turn_id:
            object.__setattr__(self, "turn_id", self.request_id)


class WSToken(BaseModel):
    type: Literal["token"] = "token"
    content: str
    request_id: str
    turn_id: str = ""  # alias for request_id

    def model_post_init(self, __context: Any) -> None:
        if not self.turn_id:
            object.__setattr__(self, "turn_id", self.request_id)


class WSGateEvent(BaseModel):
    type: Literal["gate_event"] = "gate_event"
    gate: str
    action: str
    reason: str
    fired_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = {}


class WSToolStart(BaseModel):
    type: Literal["tool_start"] = "tool_start"
    tool_name: str
    call_id: str
    params_preview: dict[str, Any] = {}


class WSToolResult(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_name: str
    call_id: str
    status: str
    result_preview: str | None = None
    execution_time_ms: float = 0.0


class WSTurnEnd(BaseModel):
    type: Literal["turn_end"] = "turn_end"
    request_id: str
    session_id: str
    turn_id: str = ""  # alias for request_id — populated by model_post_init
    blocked: bool = False
    gate_events: list[WSGateEvent] = []
    tool_events: list[WSToolResult] = []
    tokens_prompt: int = 0
    tokens_completion: int = 0
    latency_ms: float = 0.0
    iteration_count: int = 0

    def model_post_init(self, __context: Any) -> None:
        if not self.turn_id:
            object.__setattr__(self, "turn_id", self.request_id)


class WSError(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
    request_id: str | None = None


class WSPing(BaseModel):
    type: Literal["ping"] = "ping"


class WSPong(BaseModel):
    type: Literal["pong"] = "pong"
    server_time: datetime = Field(default_factory=datetime.utcnow)


# Discriminated union for all server→client messages
WSServerMessage = Annotated[
    Union[
        WSConnected,
        WSTurnStart,
        WSToken,
        WSGateEvent,
        WSToolStart,
        WSToolResult,
        WSTurnEnd,
        WSError,
        WSPing,
        WSPong,
    ],
    Field(discriminator="type"),
]

# Client→server message types


class WSChatMessage(BaseModel):
    type: Literal["chat"] = "chat"
    message: str
    request_id: str | None = None


class WSClientPing(BaseModel):
    type: Literal["ping"] = "ping"


WSClientMessage = Annotated[
    Union[WSChatMessage, WSClientPing],
    Field(discriminator="type"),
]
