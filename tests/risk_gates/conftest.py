"""Shared fixtures for risk_gates tests."""
from __future__ import annotations

import pytest

from risk_gates.schemas import RiskContext, UserRole


@pytest.fixture
def basic_risk_context() -> RiskContext:
    return RiskContext(
        session_id="test-session-001",
        user_id="user-001",
        user_role=UserRole.BASIC,
        requests_in_window=0,
        tools_called_in_window=0,
    )


@pytest.fixture
def premium_risk_context() -> RiskContext:
    return RiskContext(
        session_id="test-session-002",
        user_id="user-002",
        user_role=UserRole.PREMIUM,
        requests_in_window=0,
        tools_called_in_window=0,
    )


@pytest.fixture
def advisor_risk_context() -> RiskContext:
    return RiskContext(
        session_id="test-session-003",
        user_id="user-003",
        user_role=UserRole.ADVISOR,
        requests_in_window=0,
        tools_called_in_window=0,
    )


@pytest.fixture
def rate_limited_context() -> RiskContext:
    return RiskContext(
        session_id="test-session-004",
        user_id="user-004",
        user_role=UserRole.BASIC,
        requests_in_window=50,  # Exceeds basic limit of 30
        tools_called_in_window=0,
    )


@pytest.fixture
def mock_opa_allow_response() -> dict:
    return {
        "result": {
            "decision": {"action": "allow", "reason": "Input passed all pre-LLM checks"}
        }
    }


@pytest.fixture
def mock_opa_deny_response() -> dict:
    return {
        "result": {
            "decision": {"action": "deny", "reason": "Prompt injection detected"}
        }
    }


@pytest.fixture
def mock_opa_modify_response() -> dict:
    return {
        "result": {
            "decision": {"action": "modify", "reason": "PII detected and redacted: email"},
            "pii_found": ["email"],
            "sanitized_input": "Hello, my email is [REDACTED]",
        }
    }
