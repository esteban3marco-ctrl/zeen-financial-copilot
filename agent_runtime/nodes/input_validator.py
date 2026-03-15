"""input_validator node: parse input, build RiskContext, load UserProfile."""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage

from agent_runtime.state import AgentError, AgentState, ErrorSeverity
from agent_runtime.tracing import Attrs, agent_span
from risk_gates.schemas import RiskContext, UserRole

logger = logging.getLogger(__name__)

MAX_INPUT_LENGTH = 32_000


async def input_validator(state: AgentState) -> dict[str, Any]:
    """Validate raw input, build RiskContext, prepare initial state."""
    with agent_span("node.input_validator", **{Attrs.NODE_NAME: "input_validator"}) as span:
        # Extract latest human message
        human_messages = [m for m in state.messages if isinstance(m, HumanMessage)]
        if not human_messages:
            return {
                "error": AgentError(
                    code="NO_INPUT",
                    message="No human message found in state",
                    severity=ErrorSeverity.FATAL,
                    node="input_validator",
                ),
                "next_action": "error",
            }

        raw_input: str = str(human_messages[-1].content)

        if len(raw_input) > MAX_INPUT_LENGTH:
            return {
                "error": AgentError(
                    code="INPUT_TOO_LONG",
                    message=f"Input length {len(raw_input)} exceeds maximum {MAX_INPUT_LENGTH}",
                    severity=ErrorSeverity.ERROR,
                    node="input_validator",
                ),
                "next_action": "error",
            }

        # Build or reuse RiskContext
        risk_context = state.risk_context
        if risk_context is None:
            risk_context = RiskContext(
                session_id=state.session_memory.session_start.isoformat(),
                user_id="anonymous",
                user_role=UserRole.ANONYMOUS,
            )

        span.set_attribute(Attrs.REQUEST_ID, risk_context.request_id)
        span.set_attribute(Attrs.USER_ID, risk_context.user_id)
        span.set_attribute(Attrs.USER_ROLE, risk_context.user_role)
        span.set_attribute(Attrs.INPUT_LENGTH, len(raw_input))

        logger.info(
            "input_validator: user=%s role=%s input_len=%d",
            risk_context.user_id,
            risk_context.user_role,
            len(raw_input),
        )

        return {
            "original_input": raw_input,
            "risk_context": risk_context,
            "next_action": "continue",
        }
