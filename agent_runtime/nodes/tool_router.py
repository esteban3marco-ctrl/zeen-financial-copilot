"""tool_router node: decide whether to execute tools or generate final response."""
from __future__ import annotations

import logging
from typing import Any

from agent_runtime.state import AgentState
from agent_runtime.tracing import Attrs, agent_span

logger = logging.getLogger(__name__)


async def tool_router(state: AgentState) -> dict[str, Any]:
    """Route to tool execution or final response based on tool_calls and iteration count."""
    with agent_span("node.tool_router", **{Attrs.NODE_NAME: "tool_router"}) as span:
        has_tools = bool(state.current_tool_calls)
        under_limit = state.iteration_count < state.max_iterations

        span.set_attribute(Attrs.TOOL_ITERATION, state.iteration_count)

        if has_tools and under_limit:
            logger.info(
                "tool_router: routing to tools iter=%d/%d tools=%d",
                state.iteration_count,
                state.max_iterations,
                len(state.current_tool_calls),
            )
            return {"next_action": "route_tools"}

        if has_tools and not under_limit:
            logger.warning(
                "tool_router: max iterations reached (%d), forcing response",
                state.max_iterations,
            )

        return {"next_action": "respond"}
