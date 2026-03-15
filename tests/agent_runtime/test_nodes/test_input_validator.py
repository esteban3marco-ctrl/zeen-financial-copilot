"""Tests for input_validator node."""
from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from agent_runtime.nodes.input_validator import MAX_INPUT_LENGTH, input_validator
from agent_runtime.state import AgentState
from risk_gates.schemas import RiskContext, UserRole


def _state_with_input(text: str, ctx: RiskContext | None = None) -> AgentState:
    return AgentState(messages=[HumanMessage(content=text)], risk_context=ctx)


@pytest.mark.asyncio
class TestInputValidator:
    async def test_valid_input_returns_continue(self) -> None:
        state = _state_with_input("What is my balance?")
        result = await input_validator(state)
        assert result["next_action"] == "continue"
        assert result["original_input"] == "What is my balance?"

    async def test_no_messages_returns_error(self) -> None:
        state = AgentState()
        result = await input_validator(state)
        assert result["next_action"] == "error"
        assert result["error"].code == "NO_INPUT"

    async def test_input_too_long_returns_error(self) -> None:
        state = _state_with_input("x" * (MAX_INPUT_LENGTH + 1))
        result = await input_validator(state)
        assert result["next_action"] == "error"
        assert result["error"].code == "INPUT_TOO_LONG"

    async def test_creates_risk_context_when_missing(self) -> None:
        state = _state_with_input("Hello", ctx=None)
        result = await input_validator(state)
        assert result["next_action"] == "continue"
        assert result["risk_context"] is not None

    async def test_preserves_existing_risk_context(self) -> None:
        ctx = RiskContext(session_id="s1", user_id="u1", user_role=UserRole.PREMIUM)
        state = _state_with_input("Hello", ctx=ctx)
        result = await input_validator(state)
        assert result["risk_context"].user_id == "u1"
        assert result["risk_context"].user_role == UserRole.PREMIUM

    async def test_exact_max_length_allowed(self) -> None:
        state = _state_with_input("x" * MAX_INPUT_LENGTH)
        result = await input_validator(state)
        assert result["next_action"] == "continue"
