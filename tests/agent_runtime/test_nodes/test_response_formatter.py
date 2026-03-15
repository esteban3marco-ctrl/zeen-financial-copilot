"""Tests for response_formatter node."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent_runtime.nodes.response_formatter import response_formatter
from agent_runtime.state import AgentState


def _make_state_with_response(response: str = "Here is your balance: $500.") -> AgentState:
    return AgentState(
        messages=[
            HumanMessage(content="What is my balance?"),
            AIMessage(content=response),
        ],
        iteration_count=1,
    )


@pytest.mark.asyncio
class TestResponseFormatter:
    async def test_returns_respond_action(self) -> None:
        state = _make_state_with_response()
        result = await response_formatter(state)
        assert result["next_action"] == "respond"

    @patch("agent_runtime.nodes.response_formatter.persist_turn", new_callable=AsyncMock)
    async def test_memory_persistence_called(self, mock_persist: AsyncMock) -> None:
        from risk_gates.schemas import RiskContext, UserRole
        ctx = RiskContext(session_id="s1", user_id="u1", user_role=UserRole.BASIC)
        state = _make_state_with_response()
        state = state.model_copy(update={"risk_context": ctx})
        await response_formatter(state)
        mock_persist.assert_called_once()

    @patch("agent_runtime.nodes.response_formatter.persist_turn", new_callable=AsyncMock)
    async def test_memory_failure_does_not_block(self, mock_persist: AsyncMock) -> None:
        mock_persist.side_effect = RuntimeError("DB down")
        state = _make_state_with_response()
        # Should not raise
        result = await response_formatter(state)
        assert result["next_action"] == "respond"

    async def test_no_ai_messages_still_responds(self) -> None:
        state = AgentState(messages=[HumanMessage(content="hello")])
        result = await response_formatter(state)
        assert result["next_action"] == "respond"
