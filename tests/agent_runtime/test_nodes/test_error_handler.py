"""Tests for error_handler node."""
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from agent_runtime.nodes.error_handler import _USER_MESSAGES, error_handler
from agent_runtime.state import AgentError, AgentState, ErrorSeverity


@pytest.mark.asyncio
class TestErrorHandler:
    async def test_known_error_code_returns_mapped_message(self) -> None:
        err = AgentError(
            code="GATE_DENY",
            message="Injection detected",
            severity=ErrorSeverity.ERROR,
            node="pre_llm_gate",
        )
        state = AgentState(error=err)
        result = await error_handler(state)
        assert result["next_action"] == "respond"
        assert len(result["messages"]) == 1
        ai_msg = result["messages"][0]
        assert isinstance(ai_msg, AIMessage)
        assert _USER_MESSAGES["GATE_DENY"] in str(ai_msg.content)

    async def test_unknown_error_code_returns_generic_message(self) -> None:
        err = AgentError(
            code="UNKNOWN_CODE_XYZ",
            message="something happened",
            severity=ErrorSeverity.FATAL,
            node="some_node",
        )
        state = AgentState(error=err)
        result = await error_handler(state)
        assert "error occurred" in str(result["messages"][0].content).lower()

    async def test_no_error_in_state_handled_gracefully(self) -> None:
        state = AgentState(error=None)
        result = await error_handler(state)
        assert result["next_action"] == "respond"
        assert len(result["messages"]) == 1

    async def test_all_error_codes_have_messages(self) -> None:
        for code in ["GATE_DENY", "ALL_TOOLS_DENIED", "LLM_ERROR",
                     "INPUT_TOO_LONG", "NO_INPUT", "MISSING_RISK_CONTEXT"]:
            assert code in _USER_MESSAGES
            assert len(_USER_MESSAGES[code]) > 10
