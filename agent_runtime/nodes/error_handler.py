"""error_handler node: log error, format user-facing error response."""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from agent_runtime.state import AgentState
from agent_runtime.tracing import Attrs, agent_span, record_error

logger = logging.getLogger(__name__)

_USER_MESSAGES: dict[str, str] = {
    "GATE_DENY": "I'm unable to process this request due to compliance policy.",
    "ALL_TOOLS_DENIED": "The requested operations are not authorized for your account.",
    "LLM_ERROR": "I encountered an error generating a response. Please try again.",
    "INPUT_TOO_LONG": "Your message is too long. Please shorten it and try again.",
    "NO_INPUT": "No message was received. Please send a message.",
    "MISSING_RISK_CONTEXT": "Session context error. Please start a new conversation.",
}


async def error_handler(state: AgentState) -> dict[str, Any]:
    """Handle agent errors: log audit trail, return user-safe message."""
    with agent_span("node.error_handler", **{Attrs.NODE_NAME: "error_handler"}) as span:
        error = state.error
        if error is None:
            # Shouldn't happen, but handle gracefully
            logger.error("error_handler called with no error in state")
            error_code = "UNKNOWN"
            user_message = "An unexpected error occurred. Please try again."
        else:
            error_code = error.code
            user_message = _USER_MESSAGES.get(error_code, "An error occurred. Please try again.")
            record_error(span, error.code, error.message, error.node)
            logger.error(
                "agent_error: code=%s severity=%s node=%s message=%s",
                error.code,
                error.severity,
                error.node,
                error.message,
            )

        error_response = AIMessage(content=user_message)

        return {
            "messages": [error_response],
            "next_action": "respond",
        }
