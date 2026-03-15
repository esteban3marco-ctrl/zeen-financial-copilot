"""Tests for AgentState and supporting models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_runtime.state import (
    AgentError,
    AgentState,
    ErrorSeverity,
    SessionMemory,
    ToolResult,
    TraceMetadata,
)
from risk_gates.schemas import RiskContext, UserRole


def make_state(**kwargs) -> AgentState:
    return AgentState(**kwargs)


class TestAgentState:
    def test_default_state(self) -> None:
        state = make_state()
        assert state.messages == []
        assert state.iteration_count == 0
        assert state.max_iterations == 5
        assert state.next_action == "continue"
        assert state.error is None

    def test_iteration_count_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            make_state(iteration_count=-1)

    def test_max_iterations_bounds(self) -> None:
        with pytest.raises(ValidationError):
            make_state(max_iterations=0)
        with pytest.raises(ValidationError):
            make_state(max_iterations=11)

    def test_valid_next_actions(self) -> None:
        for action in ["continue", "route_tools", "respond", "error", "loop_back"]:
            state = make_state(next_action=action)
            assert state.next_action == action

    def test_invalid_next_action(self) -> None:
        with pytest.raises(ValidationError):
            make_state(next_action="unknown_action")

    def test_with_risk_context(self) -> None:
        ctx = RiskContext(session_id="s1", user_id="u1", user_role=UserRole.BASIC)
        state = make_state(risk_context=ctx)
        assert state.risk_context is not None
        assert state.risk_context.user_id == "u1"

    def test_error_field(self) -> None:
        err = AgentError(
            code="TEST_ERROR",
            message="test",
            severity=ErrorSeverity.ERROR,
            node="test_node",
        )
        state = make_state(error=err)
        assert state.error is not None
        assert state.error.code == "TEST_ERROR"

    def test_serialization(self) -> None:
        state = make_state(original_input="hello", iteration_count=2)
        dumped = state.model_dump(mode="json")
        assert dumped["original_input"] == "hello"
        assert dumped["iteration_count"] == 2


class TestToolResult:
    def test_valid_statuses(self) -> None:
        for status in ["success", "error", "timeout", "denied"]:
            r = ToolResult(call_id="c1", tool_name="t1", status=status)
            assert r.status == status

    def test_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            ToolResult(call_id="c1", tool_name="t1", status="unknown")

    def test_defaults(self) -> None:
        r = ToolResult(call_id="c1", tool_name="t1", status="success")
        assert r.execution_time_ms == 0.0
        assert r.sandbox_used is False
        assert r.result is None


class TestSessionMemory:
    def test_defaults(self) -> None:
        mem = SessionMemory()
        assert mem.context_window_messages == []
        assert mem.max_context_messages == 20
        assert mem.turn_count == 0

    def test_custom_max(self) -> None:
        mem = SessionMemory(max_context_messages=5)
        assert mem.max_context_messages == 5


class TestTraceMetadata:
    def test_unique_trace_ids(self) -> None:
        m1 = TraceMetadata()
        m2 = TraceMetadata()
        assert m1.trace_id != m2.trace_id

    def test_token_defaults_zero(self) -> None:
        m = TraceMetadata()
        assert m.tokens_prompt == 0
        assert m.tokens_completion == 0
        assert m.tokens_total == 0
