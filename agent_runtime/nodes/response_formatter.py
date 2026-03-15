"""response_formatter node: finalize response, persist memory, emit traces."""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from agent_runtime.state import AgentState
from agent_runtime.tracing import Attrs, agent_span
from memory.conversation import persist_turn

logger = logging.getLogger(__name__)


async def response_formatter(state: AgentState) -> dict[str, Any]:
    """Format final response and persist conversation memory."""
    with agent_span(
        "node.response_formatter",
        **{
            Attrs.NODE_NAME: "response_formatter",
            Attrs.MEMORY_TOKENS_TOTAL: state.metadata.tokens_total,
        },
    ) as span:
        ai_messages = [m for m in state.messages if isinstance(m, AIMessage)]
        response_text = str(ai_messages[-1].content) if ai_messages else ""

        span.set_attribute("staq.response.length", len(response_text))
        span.set_attribute("staq.iterations.total", state.iteration_count)

        # Persist conversation to Supabase (best-effort, non-blocking on failure)
        try:
            if state.risk_context:
                await persist_turn(
                    session_id=state.risk_context.session_id,
                    user_id=state.risk_context.user_id,
                    messages=state.messages,
                    gate_decisions=state.gate_decisions,
                    metadata=state.metadata,
                )
                span.set_attribute(
                    Attrs.MEMORY_MESSAGES_PERSISTED,
                    len(state.messages),
                )
        except Exception as exc:
            # Memory persistence failure should never block the response
            logger.warning("Memory persistence failed (non-fatal): %s", exc)

        logger.info(
            "response_formatter: response_len=%d iterations=%d tokens=%d",
            len(response_text),
            state.iteration_count,
            state.metadata.tokens_total,
        )

        return {"next_action": "respond"}
