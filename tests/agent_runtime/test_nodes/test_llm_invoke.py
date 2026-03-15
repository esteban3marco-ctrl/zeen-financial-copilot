"""Tests for llm_invoke node — mocks LLM calls."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent_runtime.nodes.llm_invoke import _parse_tool_calls, llm_invoke
from agent_runtime.state import AgentState
from risk_gates.schemas import RiskContext, UserRole


def _make_state(content: str = "What is AAPL?") -> AgentState:
    ctx = RiskContext(session_id="s1", user_id="u1", user_role=UserRole.BASIC)
    return AgentState(
        messages=[HumanMessage(content=content)],
        risk_context=ctx,
        original_input=content,
    )


class TestParseToolCalls:
    def test_extracts_tool_calls_from_ai_message(self) -> None:
        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "market_data_lookup", "args": {"ticker": "AAPL"}, "id": "call_1"}],
        )
        calls = _parse_tool_calls(ai_msg)
        assert len(calls) == 1
        assert calls[0].tool_name == "market_data_lookup"
        assert calls[0].tool_params["ticker"] == "AAPL"

    def test_empty_tool_calls(self) -> None:
        ai_msg = AIMessage(content="AAPL is at $150.", tool_calls=[])
        calls = _parse_tool_calls(ai_msg)
        assert calls == []

    def test_malformed_tool_call_skipped(self) -> None:
        ai_msg = MagicMock(spec=AIMessage)
        ai_msg.tool_calls = [{"bad_key": "no_name"}]
        calls = _parse_tool_calls(ai_msg)
        # Should not raise, may produce empty-name call
        assert isinstance(calls, list)


@pytest.mark.asyncio
class TestLLMInvoke:
    async def test_no_messages_returns_error(self) -> None:
        state = AgentState()
        result = await llm_invoke(state)
        assert result["next_action"] == "error"
        assert result["error"].code == "NO_MESSAGES"

    @patch("agent_runtime.nodes.llm_invoke.ChatAnthropic")
    async def test_successful_text_response(self, mock_llm_cls: MagicMock) -> None:
        mock_llm = AsyncMock()
        mock_response = AIMessage(content="AAPL is trading at $150.", tool_calls=[])
        mock_response.usage_metadata = {"input_tokens": 10, "output_tokens": 20}
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_cls.return_value = mock_llm

        state = _make_state()
        result = await llm_invoke(state)

        assert result["next_action"] == "respond"
        assert len(result["current_tool_calls"]) == 0
        assert result["metadata"].tokens_prompt == 10

    @patch("agent_runtime.nodes.llm_invoke.ChatAnthropic")
    async def test_response_with_tool_calls(self, mock_llm_cls: MagicMock) -> None:
        mock_llm = AsyncMock()
        mock_response = AIMessage(
            content="",
            tool_calls=[{"name": "market_data_lookup", "args": {"ticker": "AAPL"}, "id": "c1"}],
        )
        mock_response.usage_metadata = {"input_tokens": 15, "output_tokens": 5}
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_cls.return_value = mock_llm

        state = _make_state()
        result = await llm_invoke(state)

        assert result["next_action"] == "route_tools"
        assert len(result["current_tool_calls"]) == 1

    @patch("agent_runtime.nodes.llm_invoke.ChatAnthropic")
    async def test_llm_exception_returns_error(self, mock_llm_cls: MagicMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("API down"))
        mock_llm_cls.return_value = mock_llm

        state = _make_state()
        result = await llm_invoke(state)

        assert result["next_action"] == "error"
        assert result["error"].code == "LLM_ERROR"
