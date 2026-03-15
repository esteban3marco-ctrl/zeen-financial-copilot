"""AgentService: orchestrates the LangGraph agent per HTTP/WS turn."""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Any, cast

from fastapi import WebSocket

from backend.auth.models import AuthUser
from backend.config import Settings
from backend.schemas.chat import ChatResponse, MessageOut, TurnMetadataOut
from backend.schemas.gate_event import GateEventOut
from backend.schemas.tool_event import ToolEventOut

try:
    from agent_runtime.graph import build_graph
    from agent_runtime.state import AgentState
except ImportError as _e:
    build_graph = None
    AgentState = None  # type: ignore

try:
    from risk_gates.schemas import GateAction, GateDecision, RiskContext
except ImportError:
    GateAction = None  # type: ignore
    GateDecision = None  # type: ignore
    RiskContext = None  # type: ignore

try:
    from memory.conversation import load_conversation, persist_turn
except ImportError:
    load_conversation = None
    persist_turn = None

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def _gate_decisions_to_events(
    gate_decisions: dict[str, Any],
    fired_at: datetime,
) -> list[GateEventOut]:
    events: list[GateEventOut] = []
    for gate_name, decision in gate_decisions.items():
        if decision is None:
            continue
        if isinstance(decision, dict):
            action = decision.get("action", "allow")
            reason = decision.get("reason", "")
            audit = decision.get("audit") or {}
            metadata = audit.get("metadata", {}) if isinstance(audit, dict) else {}
        else:
            action = decision.action.value if hasattr(decision.action, "value") else str(decision.action)
            reason = decision.reason
            metadata = decision.audit.metadata if (hasattr(decision, "audit") and decision.audit) else {}

        events.append(
            GateEventOut(
                gate=gate_name,
                action=action,
                reason=reason,
                fired_at=fired_at,
                metadata=metadata,
            )
        )
    return events


def _tool_results_to_events(tool_results: list[Any]) -> list[ToolEventOut]:
    events: list[ToolEventOut] = []
    for tr in tool_results:
        if isinstance(tr, dict):
            tool_name = tr.get("tool_name", "unknown")
            call_id = tr.get("call_id", "")
            status = tr.get("status", "success")
            sandbox_used = tr.get("sandbox_used", False)
            exec_time = tr.get("execution_time_ms", 0.0)
            result = tr.get("result")
        else:
            tool_name = getattr(tr, "tool_name", "unknown")
            call_id = getattr(tr, "call_id", "")
            status = getattr(tr, "status", "success")
            sandbox_used = getattr(tr, "sandbox_used", False)
            exec_time = getattr(tr, "execution_time_ms", 0.0)
            result = getattr(tr, "result", None)

        preview: str | None = None
        if result is not None:
            raw = str(result)
            preview = raw[:300] if len(raw) > 300 else raw

        events.append(
            ToolEventOut(
                tool_name=tool_name,
                call_id=call_id,
                status=status,
                sandbox_used=sandbox_used,
                execution_time_ms=exec_time,
                result_preview=preview,
            )
        )
    return events


def _extract_final_content(final_state: dict[str, Any]) -> str:
    """Extract the last AI message content from the final state."""
    messages = final_state.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content"):
            content = msg.content
            if isinstance(content, str) and content:
                return content
            if isinstance(content, list):
                text_parts = [
                    p.get("text", "") if isinstance(p, dict) else str(p)
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "text" or not isinstance(p, dict)
                ]
                joined = "".join(text_parts)
                if joined:
                    return joined
        elif isinstance(msg, dict):
            content = msg.get("content", "")
            if content:
                return str(content)
    return ""


class AgentService:
    def __init__(self, settings: Settings, checkpointer: Any = None) -> None:
        self.settings = settings
        self.checkpointer = checkpointer

        if build_graph is not None:
            self.graph = build_graph(checkpointer)
        else:
            self.graph = None
            logger.warning("agent_runtime not available — AgentService running in stub mode")

    async def run_turn(
        self,
        message: str,
        session_id: str,
        auth_user: AuthUser,
        websocket: WebSocket | None = None,
        request_id: str | None = None,
    ) -> ChatResponse:
        if request_id is None:
            request_id = str(uuid.uuid4())

        start_ms = time.monotonic() * 1000
        turn_index = 0
        fired_at = datetime.utcnow()

        # Build RiskContext
        risk_ctx = None
        if RiskContext is not None:
            risk_ctx = RiskContext(
                request_id=request_id,
                session_id=session_id,
                user_id=auth_user.user_id,
                user_role=auth_user.user_role,
            )

        # Load existing conversation history
        history_messages: list[Any] = []
        if load_conversation is not None:
            conv = await load_conversation(session_id)
            if conv:
                turn_index = conv.turn_count
                # Reconstruct LangChain messages from records
                for rec in conv.messages:
                    role = rec.role if hasattr(rec, "role") else (cast(dict[str, Any], rec)).get("role", "human")
                    content = rec.content if hasattr(rec, "content") else (cast(dict[str, Any], rec)).get("content", "")
                    if role == "human":
                        history_messages.append(HumanMessage(content=content))
                    # AI messages will be reconstructed from checkpointer state

        # Build initial state dict
        human_msg = HumanMessage(content=message)
        state_dict: dict[str, Any] = {
            "messages": history_messages + [human_msg],
            "original_input": message,
            "risk_context": risk_ctx.model_dump() if risk_ctx else None,
            "gate_decisions": {},
            "tool_results": [],
            "iteration_count": 0,
            "max_iterations": 5,
            "next_action": "continue",
        }

        runnable_config: dict[str, Any] = {
            "configurable": {
                "thread_id": session_id,
                "user_id": auth_user.user_id,
            },
        }

        final_state: dict[str, Any] = {}

        if self.graph is None:
            # Stub response when runtime unavailable
            final_state = {
                "messages": [
                    HumanMessage(content=message),
                ],
                "gate_decisions": {},
                "tool_results": [],
                "metadata": {
                    "trace_id": request_id,
                    "model_used": self.settings.LLM_MODEL,
                    "tokens_prompt": 0,
                    "tokens_completion": 0,
                    "latency_ms": 0.0,
                },
                "iteration_count": 0,
            }
            content = "Agent runtime not available in current environment."
        else:
            if websocket is not None:
                # Stream events to WebSocket
                from backend.websocket.protocol import WSTurnEnd, WSTurnStart
                from backend.websocket.stream import stream_graph_to_websocket

                turn_start = WSTurnStart(request_id=request_id, session_id=session_id)
                await websocket.send_text(turn_start.model_dump_json())

                final_state = await stream_graph_to_websocket(
                    graph=self.graph,
                    state_dict=state_dict,
                    config=runnable_config,
                    websocket=websocket,
                    request_id=request_id,
                    risk_context_dict=state_dict.get("risk_context"),
                    original_input=state_dict.get("original_input", message),
                )
            else:
                # Synchronous invoke
                result = await self.graph.ainvoke(state_dict, config=runnable_config)
                if hasattr(result, "model_dump"):
                    final_state = result.model_dump()
                elif isinstance(result, dict):
                    final_state = result
                else:
                    final_state = {}

            content = _extract_final_content(final_state)
            if not content:
                content = "I processed your request."

        elapsed_ms = time.monotonic() * 1000 - start_ms

        # Extract metadata
        raw_meta = final_state.get("metadata") or {}
        if isinstance(raw_meta, dict):
            trace_id = raw_meta.get("trace_id", request_id)
            model_used = raw_meta.get("model_used", self.settings.LLM_MODEL)
            tokens_prompt = int(raw_meta.get("tokens_prompt", 0))
            tokens_completion = int(raw_meta.get("tokens_completion", 0))
        else:
            trace_id = getattr(raw_meta, "trace_id", request_id)
            model_used = getattr(raw_meta, "model_used", self.settings.LLM_MODEL)
            tokens_prompt = getattr(raw_meta, "tokens_prompt", 0)
            tokens_completion = getattr(raw_meta, "tokens_completion", 0)

        gate_decisions = final_state.get("gate_decisions", {})
        gate_events = _gate_decisions_to_events(gate_decisions, fired_at)
        tool_results = final_state.get("tool_results", [])
        tool_events = _tool_results_to_events(tool_results)
        iteration_count = final_state.get("iteration_count", 0)

        # Determine if blocked
        blocked = any(e.action == "deny" for e in gate_events)
        if blocked:
            content = "This request was blocked by the risk gate policy."

        # Persist turn asynchronously (fire and forget on error)
        if persist_turn is not None:
            try:
                from agent_runtime.state import TraceMetadata
                meta_obj = TraceMetadata(
                    trace_id=trace_id,
                    model_used=model_used,
                    tokens_prompt=tokens_prompt,
                    tokens_completion=tokens_completion,
                    tokens_total=tokens_prompt + tokens_completion,
                    latency_ms=elapsed_ms,
                )
                await persist_turn(
                    session_id=session_id,
                    user_id=auth_user.user_id,
                    messages=final_state.get("messages", [human_msg]),
                    gate_decisions=gate_decisions,
                    metadata=meta_obj,
                )
            except Exception as exc:
                logger.warning("Failed to persist turn: %s", exc)

        # Send WSTurnEnd if streaming
        if websocket is not None and self.graph is not None:
            from backend.websocket.protocol import WSTurnEnd, WSGateEvent as WSGateEventMsg, WSToolResult as WSToolResultMsg
            ws_gate_events = [
                WSGateEventMsg(gate=e.gate, action=e.action, reason=e.reason, metadata=e.metadata)
                for e in gate_events
            ]
            ws_tool_events = [
                WSToolResultMsg(
                    tool_name=e.tool_name,
                    call_id=e.call_id,
                    status=e.status,
                    result_preview=e.result_preview,
                    execution_time_ms=e.execution_time_ms,
                )
                for e in tool_events
            ]
            turn_end = WSTurnEnd(
                request_id=request_id,
                session_id=session_id,
                blocked=blocked,
                gate_events=ws_gate_events,
                tool_events=ws_tool_events,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                latency_ms=elapsed_ms,
                iteration_count=iteration_count,
            )
            await websocket.send_text(turn_end.model_dump_json())

        return ChatResponse(
            session_id=session_id,
            request_id=request_id,
            message=MessageOut(
                role="error" if blocked else "ai",
                content=content,
                turn_index=turn_index,
                created_at=fired_at,
            ),
            gate_events=gate_events,
            tool_events=tool_events,
            metadata=TurnMetadataOut(
                trace_id=trace_id,
                model_used=model_used,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                latency_ms=elapsed_ms,
                iteration_count=iteration_count,
            ),
            blocked=blocked,
        )
