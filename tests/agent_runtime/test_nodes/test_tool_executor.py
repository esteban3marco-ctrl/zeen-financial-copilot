"""Tests for tool_executor node."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import ToolMessage

from agent_runtime.nodes.tool_executor import SANDBOX_REQUIRED_TOOLS, tool_executor
from agent_runtime.state import AgentState, ToolResult
from risk_gates.schemas import RiskContext, ToolCall, UserRole


def _make_state(tool_name: str = "market_data_lookup") -> AgentState:
    ctx = RiskContext(session_id="s1", user_id="u1", user_role=UserRole.BASIC)
    return AgentState(
        current_tool_calls=[ToolCall(tool_name=tool_name, tool_params={"ticker": "AAPL"}, call_id="c1")],
        risk_context=ctx,
        iteration_count=0,
    )


@pytest.mark.asyncio
class TestToolExecutor:
    async def test_no_tool_calls_returns_respond(self) -> None:
        state = AgentState(current_tool_calls=[])
        result = await tool_executor(state)
        assert result["next_action"] == "respond"

    @patch("agent_runtime.nodes.tool_executor._execute_mcp_tool")
    async def test_successful_mcp_tool_appended(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.return_value = ToolResult(
            call_id="c1",
            tool_name="market_data_lookup",
            status="success",
            result={"ticker": "AAPL", "price": 150.25},
            execution_time_ms=80.0,
        )
        state = _make_state("market_data_lookup")
        result = await tool_executor(state)

        assert result["next_action"] == "loop_back"
        assert result["iteration_count"] == 1
        assert len(result["tool_results"]) == 1
        # ToolMessage should be appended to messages
        tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
        assert len(tool_msgs) == 1
        assert "150.25" in tool_msgs[0].content

    @patch("agent_runtime.nodes.tool_executor._execute_mcp_tool")
    async def test_error_tool_result_appended(self, mock_mcp: AsyncMock) -> None:
        mock_mcp.return_value = ToolResult(
            call_id="c1",
            tool_name="market_data_lookup",
            status="error",
            error_message="Connection refused",
        )
        state = _make_state("market_data_lookup")
        result = await tool_executor(state)

        assert result["tool_results"][0].status == "error"
        assert result["next_action"] == "loop_back"

    def test_sandbox_required_tools_set(self) -> None:
        assert "code_execute" in SANDBOX_REQUIRED_TOOLS
        assert "python_eval" in SANDBOX_REQUIRED_TOOLS
        assert "market_data_lookup" not in SANDBOX_REQUIRED_TOOLS

    @patch("agent_runtime.nodes.tool_executor._execute_sandbox_tool")
    async def test_sandbox_tool_uses_sandbox(self, mock_sandbox: AsyncMock) -> None:
        mock_sandbox.return_value = ToolResult(
            call_id="c1",
            tool_name="code_execute",
            status="success",
            result={"stdout": "42", "stderr": ""},
            sandbox_used=True,
        )
        state = _make_state("code_execute")
        result = await tool_executor(state)

        mock_sandbox.assert_called_once()
        assert result["tool_results"][0].sandbox_used is True
