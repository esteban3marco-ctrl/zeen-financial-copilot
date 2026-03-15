"""Tests for Pydantic v2 schemas in risk_gates/schemas.py."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from risk_gates.schemas import (
    AuditEntry,
    GateAction,
    GateDecision,
    GateName,
    HallucinationMarker,
    PIIMatch,
    PostLLMDecision,
    PostLLMRequest,
    PostToolDecision,
    PostToolRequest,
    PreLLMDecision,
    PreLLMRequest,
    PreToolDecision,
    PreToolRequest,
    RiskContext,
    ToolCall,
    UserRole,
)


def make_audit(gate: GateName = GateName.PRE_LLM) -> AuditEntry:
    return AuditEntry(
        gate=gate,
        action=GateAction.ALLOW,
        reason="test reason",
        request_id="req-001",
        user_id="user-001",
    )


def make_gate_decision(action: GateAction = GateAction.ALLOW) -> GateDecision:
    return GateDecision(
        action=action,
        reason="test reason",
        audit=make_audit(),
    )


class TestRiskContext:
    def test_defaults(self) -> None:
        ctx = RiskContext(session_id="s1", user_id="u1", user_role=UserRole.BASIC)
        assert ctx.requests_in_window == 0
        assert ctx.compliance_jurisdiction == "US"
        assert len(ctx.authorized_topics) > 0

    def test_request_id_auto_generated(self) -> None:
        ctx1 = RiskContext(session_id="s1", user_id="u1", user_role=UserRole.BASIC)
        ctx2 = RiskContext(session_id="s1", user_id="u1", user_role=UserRole.BASIC)
        assert ctx1.request_id != ctx2.request_id

    def test_invalid_negative_requests(self) -> None:
        with pytest.raises(ValidationError):
            RiskContext(
                session_id="s1",
                user_id="u1",
                user_role=UserRole.BASIC,
                requests_in_window=-1,
            )


class TestGateDecision:
    def test_empty_reason_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GateDecision(
                action=GateAction.ALLOW,
                reason="   ",
                audit=make_audit(),
            )

    def test_valid_allow(self) -> None:
        d = make_gate_decision(GateAction.ALLOW)
        assert d.action == GateAction.ALLOW

    def test_valid_deny(self) -> None:
        d = make_gate_decision(GateAction.DENY)
        assert d.action == GateAction.DENY


class TestPreLLMRequest:
    def test_empty_input_rejected(self, basic_risk_context: RiskContext) -> None:
        with pytest.raises(ValidationError):
            PreLLMRequest(user_input="", risk_context=basic_risk_context)

    def test_too_long_input_rejected(self, basic_risk_context: RiskContext) -> None:
        with pytest.raises(ValidationError):
            PreLLMRequest(user_input="x" * 32_001, risk_context=basic_risk_context)

    def test_valid_input(self, basic_risk_context: RiskContext) -> None:
        req = PreLLMRequest(user_input="What is my balance?", risk_context=basic_risk_context)
        assert req.user_input == "What is my balance?"


class TestPreLLMDecision:
    def test_defaults(self) -> None:
        d = PreLLMDecision(gate_decision=make_gate_decision())
        assert d.sanitized_input is None
        assert d.detected_pii == []
        assert d.injection_score == 0.0

    def test_injection_score_bounds(self) -> None:
        with pytest.raises(ValidationError):
            PreLLMDecision(gate_decision=make_gate_decision(), injection_score=1.5)


class TestToolCall:
    def test_call_id_auto_generated(self) -> None:
        t1 = ToolCall(tool_name="market_data_lookup")
        t2 = ToolCall(tool_name="market_data_lookup")
        assert t1.call_id != t2.call_id


class TestHallucinationMarker:
    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            HallucinationMarker(text_span="$1M will", marker_type="fabricated_number", confidence=2.0)

    def test_valid(self) -> None:
        m = HallucinationMarker(text_span="test", marker_type="fabricated_number", confidence=0.85)
        assert m.confidence == 0.85


class TestPostToolRequest:
    def test_negative_execution_time_rejected(self, basic_risk_context: RiskContext) -> None:
        with pytest.raises(ValidationError):
            PostToolRequest(
                tool_name="market_data_lookup",
                tool_result={"price": 100},
                execution_time_ms=-1.0,
                risk_context=basic_risk_context,
            )

    def test_any_result_type_accepted(self, basic_risk_context: RiskContext) -> None:
        for result in [{"a": 1}, [1, 2, 3], "string result", 42, None]:
            req = PostToolRequest(
                tool_name="test_tool",
                tool_result=result,
                execution_time_ms=10.0,
                risk_context=basic_risk_context,
            )
            assert req.tool_result == result
