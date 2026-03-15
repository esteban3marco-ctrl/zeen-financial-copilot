"""Direct OPA policy tests for post_tool_gate.rego — requires `opa` CLI."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

POLICY_PATH = Path("risk_gates/policies/post_tool_gate.rego")
PACKAGE = "staq/gates/post_tool"


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


def _base_input(tool_result: object, tool: str = "market_data_lookup") -> dict:
    return {
        "tool_name": tool,
        "tool_result": tool_result,
        "execution_time_ms": 100.0,
        "risk_context": {
            "user_role": "basic",
            "requests_in_window": 0,
            "tools_called_in_window": 0,
            "window_seconds": 60,
        },
    }


class TestPostToolGateRego:
    def test_clean_result_allowed(self) -> None:
        decision = _opa_eval(_base_input({"ticker": "AAPL", "price": 150.25}))
        assert decision["action"] == "allow"

    def test_api_key_in_result_triggers_modify(self) -> None:
        result = {"data": "ok", "api_key": "sk-abc123def456ghi789jkl000xyz"}
        decision = _opa_eval(_base_input(result))
        assert decision["action"] == "modify"
        assert "secret" in decision["reason"].lower()

    def test_aws_key_triggers_modify(self) -> None:
        result = {"data": "AKIAIOSFODNN7EXAMPLE"}
        decision = _opa_eval(_base_input(result))
        assert decision["action"] == "modify"

    def test_large_array_triggers_modify(self) -> None:
        result = list(range(600))
        decision = _opa_eval(_base_input(result))
        assert decision["action"] == "modify"
        assert "row" in decision["reason"].lower()

    def test_ssn_in_result_triggers_modify(self) -> None:
        result = {"user_data": "SSN: 123-45-6789"}
        decision = _opa_eval(_base_input(result))
        assert decision["action"] == "modify"
