"""llm_invoke node: call LLM, parse tool_calls, update state."""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from agent_runtime.state import AgentError, AgentState, ErrorSeverity
from agent_runtime.tracing import Attrs, agent_span
from risk_gates.schemas import ToolCall

logger = logging.getLogger(__name__)

# System prompts differentiated by role.
# These govern what the LLM can discuss; OPA gates enforce it at the policy level.
_ROLE_SYSTEM_PROMPTS: dict[str, str] = {
    "anonymous": (
        "You are a general financial information assistant. "
        "Provide only basic, publicly available financial education. "
        "Do NOT give personalized investment advice, portfolio recommendations, "
        "or specific buy/sell guidance. Always recommend consulting a licensed professional."
    ),
    "basic": (
        "You are a financial information assistant for a Basic-tier user. "
        "You can explain financial concepts, describe how markets work, and provide "
        "general educational content about investing and personal finance. "
        "Do NOT make specific investment recommendations, suggest specific securities to buy or sell, "
        "or provide personalized portfolio advice. "
        "Always include a disclaimer that this is not financial advice."
    ),
    "premium": (
        "You are a financial analysis assistant for a Premium-tier user. "
        "You can analyze portfolio compositions, explain market data, compare asset classes, "
        "discuss investment strategies at a conceptual level, and help interpret financial reports. "
        "Avoid direct buy/sell recommendations for specific securities. "
        "You may discuss risk profiles and asset allocation frameworks in general terms. "
        "Include risk disclaimers where appropriate."
    ),
    "advisor": (
        "You are a professional financial advisor assistant for a licensed financial Advisor. "
        "You may provide detailed investment recommendations, specific portfolio allocations, "
        "security-level analysis, trading strategies, and client-specific financial planning. "
        "You are authorized to discuss specific securities, ETFs, derivatives, and asset allocation. "
        "Maintain professional standards and regulatory compliance in all responses."
    ),
    "admin": (
        "You are a financial system administrator assistant with full access. "
        "You may discuss all financial topics, compliance rules, system configurations, "
        "and provide unrestricted financial analysis and recommendations."
    ),
}

_DEFAULT_SYSTEM_PROMPT = _ROLE_SYSTEM_PROMPTS["basic"]


def _get_system_prompt(risk_context: Any) -> str:
    """Return the system prompt for the user's role."""
    if risk_context is None:
        return _DEFAULT_SYSTEM_PROMPT
    role = getattr(risk_context, "user_role", None)
    if role is None and isinstance(risk_context, dict):
        role = risk_context.get("user_role", "basic")
    role_str = role.value if hasattr(role, "value") else str(role)
    return _ROLE_SYSTEM_PROMPTS.get(role_str, _DEFAULT_SYSTEM_PROMPT)


def _parse_tool_calls(ai_message: AIMessage) -> list[ToolCall]:
    """Extract structured ToolCall objects from AIMessage tool_calls."""
    calls: list[ToolCall] = []
    raw_calls: list[dict[str, Any]] = getattr(ai_message, "tool_calls", []) or []
    for raw in raw_calls:
        try:
            calls.append(
                ToolCall(
                    tool_name=raw.get("name", ""),
                    tool_params=raw.get("args", {}),
                    call_id=raw.get("id", ""),
                )
            )
        except Exception as exc:
            logger.warning("Failed to parse tool_call %r: %s", raw, exc)
    return calls


async def llm_invoke(state: AgentState, config: Optional[RunnableConfig] = None) -> dict[str, Any]:
    """Invoke the LLM with current message history."""
    with agent_span("node.llm_invoke", **{Attrs.NODE_NAME: "llm_invoke"}) as span:
        if not state.messages:
            return {
                "error": AgentError(
                    code="NO_MESSAGES",
                    message="Message list is empty at llm_invoke",
                    severity=ErrorSeverity.FATAL,
                    node="llm_invoke",
                ),
                "next_action": "error",
            }

        # Build context window from session memory
        context_messages = state.session_memory.context_window_messages or state.messages

        # Prepend role-aware system message if not already present
        system_prompt = _get_system_prompt(state.risk_context)
        if not context_messages or not isinstance(context_messages[0], SystemMessage):
            context_messages = [SystemMessage(content=system_prompt)] + list(context_messages)
        elif isinstance(context_messages[0], SystemMessage):
            # Replace existing system message with role-specific one
            context_messages = [SystemMessage(content=system_prompt)] + list(context_messages[1:])

        model_name = os.getenv("STAQ_LLM_MODEL", "claude-sonnet-4-6")
        llm = ChatAnthropic(  # type: ignore[call-arg]
            model_name=model_name,
            temperature=0.1,
            max_tokens_to_sample=4096,
            streaming=True,
        )

        start_ms = time.monotonic() * 1000
        try:
            response = await llm.ainvoke(context_messages, config=config)
        except Exception as exc:
            logger.exception("LLM invocation failed")
            return {
                "error": AgentError(
                    code="LLM_ERROR",
                    message=f"LLM call failed: {exc}",
                    severity=ErrorSeverity.FATAL,
                    node="llm_invoke",
                ),
                "next_action": "error",
            }
        latency_ms = time.monotonic() * 1000 - start_ms

        ai_message: AIMessage = response
        tool_calls = _parse_tool_calls(ai_message)

        # Extract token usage
        usage = getattr(response, "usage_metadata", {}) or {}
        tokens_prompt = usage.get("input_tokens", 0)
        tokens_completion = usage.get("output_tokens", 0)

        role_str = "unknown"
        if state.risk_context:
            r = getattr(state.risk_context, "user_role", None)
            role_str = r.value if hasattr(r, "value") else str(r)

        span.set_attribute(Attrs.LLM_MODEL, model_name)
        span.set_attribute(Attrs.LLM_TOKENS_PROMPT, tokens_prompt)
        span.set_attribute(Attrs.LLM_TOKENS_COMPLETION, tokens_completion)
        span.set_attribute(Attrs.LLM_TOOL_COUNT, len(tool_calls))

        # Update trace metadata
        metadata = state.metadata.model_copy(
            update={
                "model_used": model_name,
                "tokens_prompt": state.metadata.tokens_prompt + tokens_prompt,
                "tokens_completion": state.metadata.tokens_completion + tokens_completion,
                "tokens_total": state.metadata.tokens_total + tokens_prompt + tokens_completion,
                "latency_ms": state.metadata.latency_ms + latency_ms,
            }
        )

        next_action = "route_tools" if tool_calls else "respond"
        logger.info(
            "llm_invoke: model=%s role=%s tokens=%d tool_calls=%d",
            model_name,
            role_str,
            tokens_prompt + tokens_completion,
            len(tool_calls),
        )

        return {
            "messages": [ai_message],
            "current_tool_calls": tool_calls,
            "metadata": metadata,
            "next_action": next_action,
        }
