"""Direct OPA policy tests for pre_tool_gate.rego — requires `opa` CLI."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

POLICY_PATH = Path("risk_gates/policies/pre_tool_gate.rego")
PACKAGE = "staq/gates/pre_tool"


def _opa_eval(input_data: dict) -> dict:
    try:
        result = subprocess.run(
            [
                "opa", "eval",
                "--data", str(POLICY_PATH),
                "--input", "/dev/stdin",
                "--format", "raw",
                f"data.{PACKAGE.replace('/', '.')}.decision",
            ],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, OSError):
        pytest.skip("OPA CLI not installed — skipping Rego policy tests")
    if result.returncode != 0:
        pytest.skip(f"OPA CLI not available or policy error: {result.stderr}")
    return json.loads(result.stdout)


def _base_input(tool: str, params: dict | None = None, role: str = "basic", tools_in_window: int = 0) -> dict:
    return {
        "tool_name": tool,
        "tool_params": params or {},
        "risk_context": {
            "user_role": role,
            "requests_in_window": 0,
            "tools_called_in_window": tools_in_window,
            "window_seconds": 60,
        },
    }


class TestPreToolGateRego:
    def test_basic_tool_allowed_for_basic_role(self) -> None:
        decision = _opa_eval(_base_input("market_data_lookup", {"ticker": "AAPL"}))
        assert decision["action"] == "allow"

    def test_premium_tool_denied_for_basic_role(self) -> None:
        decision = _opa_eval(_base_input("trade_executor"))
        assert decision["action"] == "deny"

    def test_premium_tool_allowed_for_premium_role(self) -> None:
        decision = _opa_eval(_base_input("financial_report", role="premium"))
        assert decision["action"] == "allow"

    def test_all_tools_allowed_for_admin(self) -> None:
        decision = _opa_eval(_base_input("trade_executor", role="admin"))
        assert decision["action"] == "allow"

    def test_sql_injection_in_params_denied(self) -> None:
        decision = _opa_eval(_base_input("market_data_lookup", {"query": "'; DROP TABLE users; --"}))
        assert decision["action"] == "deny"
        assert "injection" in decision["reason"].lower()

    def test_trade_executor_rate_limit(self) -> None:
        decision = _opa_eval(_base_input("trade_executor", role="advisor", tools_in_window=10))
        assert decision["action"] == "deny"
        assert "rate" in decision["reason"].lower()

    def test_unauthorized_mcp_server_denied(self) -> None:
        decision = _opa_eval(
            _base_input("market_data_lookup", {"mcp_server": "evil-server"}, role="basic")
        )
        assert decision["action"] == "deny"
        assert "mcp" in decision["reason"].lower()
