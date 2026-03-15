"""Tests for pre_tool gate Python-side logic (param sanitization)."""
from __future__ import annotations

import pytest
import respx
import httpx

from risk_gates.gates.pre_tool import _sanitize_params, run_pre_tool_gate
from risk_gates.schemas import (
    GateAction,
    PreToolRequest,
    RiskContext,
    UserRole,
)


def _make_ctx(role: UserRole = UserRole.BASIC) -> RiskContext:
    return RiskContext(session_id="s1", user_id="u1", user_role=role)


class TestSanitizeParams:
    def test_html_escaped(self) -> None:
        params = {"query": "<script>alert('xss')</script>"}
        result = _sanitize_params(params)
        assert "<script>" not in result["query"]
        assert "&lt;" in result["query"]

    def test_control_chars_stripped(self) -> None:
        params = {"input": "hello\x00world\x1f"}
        result = _sanitize_params(params)
        assert "\x00" not in result["input"]
        assert "\x1f" not in result["input"]
        assert "helloworld" in result["input"]

    def test_non_string_values_preserved(self) -> None:
        params = {"count": 10, "enabled": True, "data": [1, 2, 3]}
        result = _sanitize_params(params)
        assert result["count"] == 10
        assert result["enabled"] is True
        assert result["data"] == [1, 2, 3]

    def test_clean_string_unchanged(self) -> None:
        params = {"ticker": "AAPL", "limit": "100"}
        result = _sanitize_params(params)
        assert result["ticker"] == "AAPL"
        assert result["limit"] == "100"


@pytest.mark.asyncio
class TestRunPreToolGate:
    @respx.mock
    async def test_sanitized_params_returned_on_allow(self) -> None:
        respx.post("http://localhost:8181/v1/data/staq/gates/pre_tool").mock(
            return_value=httpx.Response(
                200,
                json={"result": {"decision": {"action": "allow", "reason": "Authorized"}}},
            )
        )
        ctx = _make_ctx()
        req = PreToolRequest(
            tool_name="market_data_lookup",
            tool_params={"ticker": "AAPL<>"},
            risk_context=ctx,
        )
        result = await run_pre_tool_gate(req)
        assert result.gate_decision.action == GateAction.ALLOW
        assert result.sanitized_params is not None
        assert "<>" not in result.sanitized_params["ticker"]

    @respx.mock
    async def test_denied_returns_no_sanitized_params(self) -> None:
        respx.post("http://localhost:8181/v1/data/staq/gates/pre_tool").mock(
            return_value=httpx.Response(
                200,
                json={"result": {"decision": {"action": "deny", "reason": "Not authorized"}}},
            )
        )
        ctx = _make_ctx()
        req = PreToolRequest(
            tool_name="trade_executor",
            tool_params={"action": "buy"},
            risk_context=ctx,
        )
        result = await run_pre_tool_gate(req)
        assert result.gate_decision.action == GateAction.DENY
        assert result.sanitized_params is None
