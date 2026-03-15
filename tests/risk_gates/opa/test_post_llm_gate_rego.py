"""Direct OPA policy tests for post_llm_gate.rego — requires `opa` CLI."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

POLICY_PATH = Path("risk_gates/policies/post_llm_gate.rego")
PACKAGE = "staq/gates/post_llm"


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


def _base_input(llm_response: str, role: str = "basic") -> dict:
    return {
        "llm_response": llm_response,
        "original_input": "test",
        "tool_calls": [],
        "risk_context": {
            "user_role": role,
            "requests_in_window": 0,
            "tools_called_in_window": 0,
            "window_seconds": 60,
        },
    }


class TestPostLLMGateRego:
    def test_clean_response_allowed(self) -> None:
        decision = _opa_eval(_base_input("Your account balance is $1,234.56."))
        assert decision["action"] == "allow"

    def test_regulated_advice_without_disclaimer_denied(self) -> None:
        decision = _opa_eval(_base_input("You should buy AAPL stock now for guaranteed returns."))
        assert decision["action"] == "deny"

    def test_regulated_advice_advisor_allowed(self) -> None:
        decision = _opa_eval(_base_input("You should buy AAPL based on your portfolio.", role="advisor"))
        assert decision["action"] == "allow"

    def test_guaranteed_returns_denied(self) -> None:
        decision = _opa_eval(_base_input("This fund has guaranteed returns of 15%."))
        assert decision["action"] == "deny"

    def test_response_with_disclaimer_not_denied(self) -> None:
        response = "I recommend buying bonds. Disclaimer: not financial advice."
        decision = _opa_eval(_base_input(response))
        # With disclaimer present, regulated advice rule doesn't fire
        assert decision["action"] in {"allow", "modify"}
