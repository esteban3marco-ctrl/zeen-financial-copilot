"""post_tool_gate node: sanitize tool results via OPA."""
from __future__ import annotations

import logging
from typing import Any

from agent_runtime.state import AgentState, ToolResult
from agent_runtime.tracing import Attrs, agent_span
from risk_gates.gates.post_tool import run_post_tool_gate
from risk_gates.schemas import GateAction, GateName, PostToolRequest

logger = logging.getLogger(__name__)


async def post_tool_gate(state: AgentState) -> dict[str, Any]:
    """Evaluate OPA post-tool gate for each tool result."""
    with agent_span("node.post_tool_gate", **{Attrs.NODE_NAME: "post_tool_gate"}) as span:
        if state.risk_context is None or not state.tool_results:
            return {"next_action": "loop_back"}

        gate_decisions = dict(state.gate_decisions)
        sanitized_results: list[ToolResult] = []

        # Only process the latest batch (not all historical results)
        latest_batch = state.tool_results[-len(state.current_tool_calls):]

        for tool_result in latest_batch:
            if tool_result.status != "success":
                sanitized_results.append(tool_result)
                continue

            request = PostToolRequest(
                tool_name=tool_result.tool_name,
                tool_result=tool_result.result,
                execution_time_ms=tool_result.execution_time_ms,
                risk_context=state.risk_context,
            )

            decision = await run_post_tool_gate(request)
            gate_key = f"{GateName.POST_TOOL}:{tool_result.call_id}"
            gate_decisions[gate_key] = decision.gate_decision

            span.set_attribute(Attrs.GATE_NAME, GateName.POST_TOOL)
            span.set_attribute(Attrs.GATE_ACTION, decision.gate_decision.action)
            span.set_attribute(Attrs.TOOL_NAME, tool_result.tool_name)

            if decision.gate_decision.action == GateAction.DENY:
                logger.warning(
                    "post_tool_gate DENY: tool=%s reason=%s",
                    tool_result.tool_name,
                    decision.gate_decision.reason,
                )
                sanitized_results.append(
                    tool_result.model_copy(
                        update={
                            "status": "denied",
                            "result": None,
                            "error_message": decision.gate_decision.reason,
                        }
                    )
                )
            elif decision.gate_decision.action == GateAction.MODIFY:
                sanitized_results.append(
                    tool_result.model_copy(
                        update={"result": decision.sanitized_result}
                    )
                )
                logger.info(
                    "post_tool_gate MODIFY: tool=%s secrets_redacted=%d",
                    tool_result.tool_name,
                    len(decision.secrets_found),
                )
            else:
                sanitized_results.append(tool_result)

        # Replace the latest batch with sanitized versions
        all_results = list(state.tool_results[: -len(latest_batch)]) + sanitized_results

        return {
            "tool_results": all_results,
            "gate_decisions": gate_decisions,
            "next_action": "loop_back",
        }
