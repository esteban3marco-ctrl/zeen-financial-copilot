"""pre_tool_gate node: authorize each tool call via OPA."""
from __future__ import annotations

import logging
from typing import Any

from agent_runtime.state import AgentError, AgentState, ErrorSeverity
from agent_runtime.tracing import Attrs, agent_span
from risk_gates.gates.pre_tool import run_pre_tool_gate
from risk_gates.schemas import GateAction, GateName, PreToolRequest, ToolCall

logger = logging.getLogger(__name__)


async def pre_tool_gate(state: AgentState) -> dict[str, Any]:
    """Evaluate OPA pre-tool gate for each pending tool call."""
    with agent_span("node.pre_tool_gate", **{Attrs.NODE_NAME: "pre_tool_gate"}) as span:
        if state.risk_context is None:
            return {
                "error": AgentError(
                    code="MISSING_RISK_CONTEXT",
                    message="risk_context is None at pre_tool_gate",
                    severity=ErrorSeverity.FATAL,
                    node="pre_tool_gate",
                ),
                "next_action": "error",
            }

        gate_decisions = dict(state.gate_decisions)
        authorized_calls: list[ToolCall] = []
        denied_any = False

        for tool_call in state.current_tool_calls:
            request = PreToolRequest(
                tool_name=tool_call.tool_name,
                tool_params=tool_call.tool_params,
                risk_context=state.risk_context,
            )

            decision = await run_pre_tool_gate(request)
            gate_key = f"{GateName.PRE_TOOL}:{tool_call.call_id}"
            gate_decisions[gate_key] = decision.gate_decision

            span.set_attribute(Attrs.GATE_NAME, GateName.PRE_TOOL)
            span.set_attribute(Attrs.GATE_ACTION, decision.gate_decision.action)
            span.set_attribute(Attrs.TOOL_NAME, tool_call.tool_name)

            if decision.gate_decision.action == GateAction.DENY:
                logger.warning(
                    "pre_tool_gate DENY: tool=%s reason=%s",
                    tool_call.tool_name,
                    decision.gate_decision.reason,
                )
                denied_any = True
                # Denied tools are dropped; execution continues with authorized ones
                continue

            # Use sanitized params if MODIFY action
            if decision.gate_decision.action == GateAction.MODIFY and decision.sanitized_params:
                authorized_calls.append(
                    ToolCall(
                        tool_name=tool_call.tool_name,
                        tool_params=decision.sanitized_params,
                        call_id=tool_call.call_id,
                    )
                )
            else:
                authorized_calls.append(tool_call)

        # If ALL tools were denied, treat as error
        if denied_any and not authorized_calls:
            return {
                "gate_decisions": gate_decisions,
                "error": AgentError(
                    code="ALL_TOOLS_DENIED",
                    message="All requested tool calls were denied by the pre-tool gate",
                    severity=ErrorSeverity.ERROR,
                    node="pre_tool_gate",
                ),
                "next_action": "error",
            }

        return {
            "current_tool_calls": authorized_calls,
            "gate_decisions": gate_decisions,
            "next_action": "continue",
        }
