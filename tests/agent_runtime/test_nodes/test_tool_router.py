"""Tests for tool_router node."""
from __future__ import annotations

import pytest

from agent_runtime.nodes.tool_router import tool_router
from agent_runtime.state import AgentState
from risk_gates.schemas import ToolCall


def _make_tool_call(name: str = "market_data_lookup") -> ToolCall:
    return ToolCall(tool_name=name, tool_params={"ticker": "AAPL"})


@pytest.mark.asyncio
class TestToolRouter:
    async def test_routes_to_tools_when_calls_present(self) -> None:
        state = AgentState(
            current_tool_calls=[_make_tool_call()],
            iteration_count=0,
            max_iterations=5,
        )
        result = await tool_router(state)
        assert result["next_action"] == "route_tools"

    async def test_routes_to_respond_when_no_tools(self) -> None:
        state = AgentState(
            current_tool_calls=[],
            iteration_count=0,
            max_iterations=5,
        )
        result = await tool_router(state)
        assert result["next_action"] == "respond"

    async def test_routes_to_respond_at_max_iterations(self) -> None:
        state = AgentState(
            current_tool_calls=[_make_tool_call()],
            iteration_count=5,
            max_iterations=5,
        )
        result = await tool_router(state)
        assert result["next_action"] == "respond"

    async def test_routes_to_tools_under_max_iterations(self) -> None:
        state = AgentState(
            current_tool_calls=[_make_tool_call()],
            iteration_count=4,
            max_iterations=5,
        )
        result = await tool_router(state)
        assert result["next_action"] == "route_tools"
