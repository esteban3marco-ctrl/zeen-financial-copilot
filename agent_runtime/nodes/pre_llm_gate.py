"""pre_llm_gate node: OPA gate + PII redaction before LLM invocation."""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage

from agent_runtime.state import AgentError, AgentState, ErrorSeverity
from agent_runtime.tracing import Attrs, agent_span
from risk_gates.gates.pre_llm import run_pre_llm_gate
from risk_gates.schemas import GateAction, GateName, PreLLMRequest

logger = logging.getLogger(__name__)


async def pre_llm_gate(state: AgentState) -> dict[str, Any]:
    """Evaluate pre-LLM OPA gate; redact PII if needed."""
    with agent_span("node.pre_llm_gate", **{Attrs.NODE_NAME: "pre_llm_gate"}) as span:
        if state.risk_context is None:
            return {
                "error": AgentError(
                    code="MISSING_RISK_CONTEXT",
                    message="risk_context is None at pre_llm_gate",
                    severity=ErrorSeverity.FATAL,
                    node="pre_llm_gate",
                ),
                "next_action": "error",
            }

        request = PreLLMRequest(
            user_input=state.original_input,
            risk_context=state.risk_context,
        )

        decision = await run_pre_llm_gate(request)

        span.set_attribute(Attrs.GATE_NAME, GateName.PRE_LLM)
        span.set_attribute(Attrs.GATE_ACTION, decision.gate_decision.action)
        span.set_attribute(Attrs.INJECTION_SCORE, decision.injection_score)
        span.set_attribute(Attrs.PII_COUNT, len(decision.detected_pii))

        gate_decisions = dict(state.gate_decisions)
        gate_decisions[GateName.PRE_LLM] = decision.gate_decision

        if decision.gate_decision.action == GateAction.DENY:
            logger.warning(
                "pre_llm_gate DENY: %s user=%s",
                decision.gate_decision.reason,
                state.risk_context.user_id,
            )
            return {
                "gate_decisions": gate_decisions,
                "error": AgentError(
                    code="GATE_DENY",
                    message=decision.gate_decision.reason,
                    severity=ErrorSeverity.ERROR,
                    node="pre_llm_gate",
                    details={"gate": GateName.PRE_LLM, "injection_score": decision.injection_score},
                ),
                "next_action": "error",
            }

        # If PII was redacted, update the last HumanMessage in state
        updates: dict[str, Any] = {"gate_decisions": gate_decisions, "next_action": "continue"}
        if decision.gate_decision.action == GateAction.MODIFY and decision.sanitized_input:
            sanitized_msg = HumanMessage(content=decision.sanitized_input)
            updates["messages"] = [sanitized_msg]
            updates["original_input"] = decision.sanitized_input
            logger.info(
                "pre_llm_gate MODIFY: redacted %d PII items",
                len(decision.detected_pii),
            )

        return updates
