"""post_llm_gate node: OPA compliance check on LLM output."""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from agent_runtime.state import AgentError, AgentState, ErrorSeverity
from agent_runtime.tracing import Attrs, agent_span
from risk_gates.gates.post_llm import run_post_llm_gate
from risk_gates.schemas import GateAction, GateName, PostLLMRequest

logger = logging.getLogger(__name__)


async def post_llm_gate(state: AgentState) -> dict[str, Any]:
    """Evaluate post-LLM OPA gate; inject disclaimer if needed."""
    with agent_span("node.post_llm_gate", **{Attrs.NODE_NAME: "post_llm_gate"}) as span:
        if state.risk_context is None:
            return {
                "error": AgentError(
                    code="MISSING_RISK_CONTEXT",
                    message="risk_context is None at post_llm_gate",
                    severity=ErrorSeverity.FATAL,
                    node="post_llm_gate",
                ),
                "next_action": "error",
            }

        # Get the latest AI message
        ai_messages = [m for m in state.messages if isinstance(m, AIMessage)]
        if not ai_messages:
            return {"next_action": state.next_action}

        latest_ai_msg = ai_messages[-1]
        llm_response_text: str = str(latest_ai_msg.content)

        request = PostLLMRequest(
            llm_response=llm_response_text,
            tool_calls=state.current_tool_calls,
            risk_context=state.risk_context,
            original_input=state.original_input,
        )

        decision = await run_post_llm_gate(request)

        span.set_attribute(Attrs.GATE_NAME, GateName.POST_LLM)
        span.set_attribute(Attrs.GATE_ACTION, decision.gate_decision.action)
        span.set_attribute(Attrs.COMPLIANCE_FLAGS, str(decision.compliance_flags))

        gate_decisions = dict(state.gate_decisions)
        gate_decisions[GateName.POST_LLM] = decision.gate_decision

        if decision.gate_decision.action == GateAction.DENY:
            logger.warning(
                "post_llm_gate DENY: %s user=%s",
                decision.gate_decision.reason,
                state.risk_context.user_id,
            )
            return {
                "gate_decisions": gate_decisions,
                "error": AgentError(
                    code="GATE_DENY",
                    message=decision.gate_decision.reason,
                    severity=ErrorSeverity.ERROR,
                    node="post_llm_gate",
                    details={"compliance_flags": decision.compliance_flags},
                ),
                "next_action": "error",
            }

        updates: dict[str, Any] = {"gate_decisions": gate_decisions}

        if decision.gate_decision.action == GateAction.MODIFY and decision.modified_response:
            modified_msg = AIMessage(content=decision.modified_response)
            updates["messages"] = [modified_msg]
            logger.info(
                "post_llm_gate MODIFY: flags=%s",
                decision.compliance_flags,
            )

        # Preserve next_action from llm_invoke (route_tools or respond)
        updates["next_action"] = state.next_action
        return updates
