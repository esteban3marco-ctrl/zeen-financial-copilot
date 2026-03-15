"""Tests for post_tool gate Python-side logic (secret redaction, truncation)."""
from __future__ import annotations

import pytest
import respx
import httpx

from risk_gates.gates.post_tool import _MAX_ROWS, _redact_secrets, _truncate_result, run_post_tool_gate
from risk_gates.schemas import (
    GateAction,
    PostToolRequest,
    RiskContext,
    UserRole,
)


def _make_ctx() -> RiskContext:
    return RiskContext(session_id="s1", user_id="u1", user_role=UserRole.BASIC)


class TestRedactSecrets:
    def test_api_key_redacted(self) -> None:
        text = "Result: api_key=sk-abc123def456ghi789jkl000"
        result, found = _redact_secrets(text)
        assert "sk-abc123def456ghi789jkl000" not in result
        assert "api_key" in found

    def test_aws_key_redacted(self) -> None:
        text = "AWS key: AKIAIOSFODNN7EXAMPLE"
        result, found = _redact_secrets(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "aws_key" in found

    def test_no_secrets_unchanged(self) -> None:
        text = '{"ticker": "AAPL", "price": 150.25}'
        result, found = _redact_secrets(text)
        assert result == text
        assert found == []

    def test_multiple_secrets_all_redacted(self) -> None:
        text = "api_key=abc123def456ghi789jkl password=mysecret123"
        result, found = _redact_secrets(text)
        assert "abc123def456" not in result
        assert "mysecret123" not in result
        assert len(found) >= 1


class TestTruncateResult:
    def test_list_truncated(self) -> None:
        data = list(range(600))
        result = _truncate_result(data)
        assert isinstance(result, list)
        assert len(result) == _MAX_ROWS

    def test_short_list_unchanged(self) -> None:
        data = [1, 2, 3]
        result = _truncate_result(data)
        assert result == [1, 2, 3]

    def test_dict_with_rows_truncated(self) -> None:
        data = {"rows": list(range(600)), "total": 600}
        result = _truncate_result(data)
        assert len(result["rows"]) == _MAX_ROWS
        assert result.get("truncated") is True

    def test_non_list_result_unchanged(self) -> None:
        data = {"ticker": "AAPL", "price": 150.25}
        result = _truncate_result(data)
        assert result == data


@pytest.mark.asyncio
class TestRunPostToolGate:
    @respx.mock
    async def test_clean_result_allowed(self) -> None:
        respx.post("http://localhost:8181/v1/data/staq/gates/post_tool").mock(
            return_value=httpx.Response(
                200,
                json={"result": {"decision": {"action": "allow", "reason": "Clean result"}}},
            )
        )
        ctx = _make_ctx()
        req = PostToolRequest(
            tool_name="market_data_lookup",
            tool_result={"ticker": "AAPL", "price": 150.25},
            execution_time_ms=80.0,
            risk_context=ctx,
        )
        result = await run_post_tool_gate(req)
        assert result.gate_decision.action == GateAction.ALLOW

    @respx.mock
    async def test_secret_in_result_triggers_python_redaction(self) -> None:
        respx.post("http://localhost:8181/v1/data/staq/gates/post_tool").mock(
            return_value=httpx.Response(
                200,
                json={
                    "result": {
                        "decision": {"action": "modify", "reason": "Secrets detected"},
                        "secrets_found": ["api_key"],
                    }
                },
            )
        )
        ctx = _make_ctx()
        req = PostToolRequest(
            tool_name="external_api",
            tool_result="response api_key=sk-abc123def456ghi789jkl000 data ok",
            execution_time_ms=50.0,
            risk_context=ctx,
        )
        result = await run_post_tool_gate(req)
        assert result.gate_decision.action == GateAction.MODIFY
        assert result.sanitized_result is not None
        assert "sk-abc123def456ghi789jkl000" not in str(result.sanitized_result)
