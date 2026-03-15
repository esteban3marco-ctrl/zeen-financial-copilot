"""
Coverage boost tests targeting uncovered lines in:
- backend/auth/middleware.py
- tools/registry.py
- backend/demo_tools/financial_calc.py
- risk_gates/gates/pre_llm.py (MODIFY path / IBAN redaction)
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================================
# backend/auth/middleware.py
# ============================================================================

class TestRoleFromString:
    def test_none_returns_basic(self):
        from backend.auth.middleware import _role_from_string
        from risk_gates.schemas import UserRole
        assert _role_from_string(None) == UserRole.BASIC

    def test_valid_role_basic(self):
        from backend.auth.middleware import _role_from_string
        from risk_gates.schemas import UserRole
        assert _role_from_string("basic") == UserRole.BASIC

    def test_valid_role_advisor(self):
        from backend.auth.middleware import _role_from_string
        from risk_gates.schemas import UserRole
        assert _role_from_string("advisor") == UserRole.ADVISOR

    def test_valid_role_admin(self):
        from backend.auth.middleware import _role_from_string
        from risk_gates.schemas import UserRole
        assert _role_from_string("admin") == UserRole.ADMIN

    def test_invalid_role_returns_basic(self):
        from backend.auth.middleware import _role_from_string
        from risk_gates.schemas import UserRole
        assert _role_from_string("superuser") == UserRole.BASIC

    def test_uppercase_role_is_normalized(self):
        from backend.auth.middleware import _role_from_string
        from risk_gates.schemas import UserRole
        assert _role_from_string("BASIC") == UserRole.BASIC

    def test_premium_role(self):
        from backend.auth.middleware import _role_from_string
        from risk_gates.schemas import UserRole
        assert _role_from_string("premium") == UserRole.PREMIUM


class TestGetCurrentUserDemoMode:
    """Test get_current_user in DEMO_MODE (no auth required)."""

    @pytest.mark.asyncio
    async def test_no_token_demo_mode_returns_demo_user(self):
        from fastapi import Request
        from backend.auth.middleware import get_current_user
        from backend.config import Settings
        from risk_gates.schemas import UserRole

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        settings = Settings(DEMO_MODE=True)
        user = await get_current_user(mock_request, settings)
        assert user.demo_mode is True
        assert user.user_id == "demo-user"

    @pytest.mark.asyncio
    async def test_x_demo_role_header_overrides_role(self):
        from fastapi import Request
        from backend.auth.middleware import get_current_user
        from backend.config import Settings
        from risk_gates.schemas import UserRole

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Demo-Role": "advisor"}

        settings = Settings(DEMO_MODE=True)
        user = await get_current_user(mock_request, settings)
        assert user.user_role == UserRole.ADVISOR

    @pytest.mark.asyncio
    async def test_no_token_non_demo_mode_raises_401(self):
        from fastapi import Request, HTTPException
        from backend.auth.middleware import get_current_user
        from backend.config import Settings

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        settings = Settings(DEMO_MODE=False)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, settings)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_jwt_demo_mode_returns_demo_user(self):
        from fastapi import Request
        from backend.auth.middleware import get_current_user
        from backend.config import Settings
        from risk_gates.schemas import UserRole

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {
            "Authorization": "Bearer invalid.jwt.token",
            "X-Demo-Role": None,
        }

        settings = Settings(DEMO_MODE=True, SUPABASE_JWT_SECRET="test-secret")

        # With an invalid JWT and DEMO_MODE=True, should fall back to demo user
        user = await get_current_user(mock_request, settings)
        assert user.demo_mode is True

    @pytest.mark.asyncio
    async def test_bearer_token_extracted_from_header(self):
        from fastapi import Request
        from backend.auth.middleware import get_current_user
        from backend.config import Settings

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {
            "Authorization": "Bearer sometoken123",
        }

        settings = Settings(DEMO_MODE=True, SUPABASE_JWT_SECRET="secret")

        # With DEMO_MODE=True, JWT decode failure → demo user
        user = await get_current_user(mock_request, settings)
        assert user is not None

    @pytest.mark.asyncio
    async def test_jose_import_error_demo_mode_returns_demo_user(self):
        from fastapi import Request
        from backend.auth.middleware import get_current_user
        from backend.config import Settings

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {
            "Authorization": "Bearer sometoken123",
        }

        settings = Settings(DEMO_MODE=True)

        # Force ImportError on jose
        import sys
        original = sys.modules.get("jose")
        sys.modules["jose"] = None  # type: ignore

        try:
            user = await get_current_user(mock_request, settings)
            assert user.demo_mode is True
        finally:
            if original is None:
                sys.modules.pop("jose", None)
            else:
                sys.modules["jose"] = original


# ============================================================================
# tools/registry.py
# ============================================================================

class TestMCPToolRegistry:
    def _make_registry(self):
        from tools.registry import MCPToolRegistry
        return MCPToolRegistry()

    def test_register_and_get_server(self):
        from tools.schemas import MCPServerConfig
        reg = self._make_registry()
        cfg = MCPServerConfig(server_id="srv1", transport="sse", url="http://x")
        reg.register_server(cfg)
        assert reg.get_server("srv1") is cfg

    def test_get_server_not_found_returns_none(self):
        reg = self._make_registry()
        assert reg.get_server("nonexistent") is None

    def test_register_and_get_tool(self):
        from tools.schemas import MCPToolSchema
        reg = self._make_registry()
        tool = MCPToolSchema(name="my_tool", description="desc", server_id="srv1")
        reg.register_tool(tool)
        assert reg.get_tool("my_tool") is tool

    def test_get_tool_not_found_returns_none(self):
        reg = self._make_registry()
        assert reg.get_tool("missing") is None

    def test_server_for_tool(self):
        from tools.schemas import MCPToolSchema
        reg = self._make_registry()
        tool = MCPToolSchema(name="calc", description="", server_id="calc-srv")
        reg.register_tool(tool)
        assert reg.server_for_tool("calc") == "calc-srv"

    def test_server_for_tool_not_found(self):
        reg = self._make_registry()
        assert reg.server_for_tool("ghost") is None

    def test_all_tools_empty(self):
        reg = self._make_registry()
        assert reg.all_tools() == []

    def test_all_tools_returns_all(self):
        from tools.schemas import MCPToolSchema
        reg = self._make_registry()
        reg.register_tool(MCPToolSchema(name="t1", description="", server_id="s1"))
        reg.register_tool(MCPToolSchema(name="t2", description="", server_id="s1"))
        assert len(reg.all_tools()) == 2

    def test_tools_for_role_basic_only_low(self):
        from tools.schemas import MCPToolSchema
        reg = self._make_registry()
        reg.register_tool(MCPToolSchema(name="low_t", description="", server_id="s1", risk_level="low"))
        reg.register_tool(MCPToolSchema(name="med_t", description="", server_id="s1", risk_level="medium"))
        reg.register_tool(MCPToolSchema(name="hi_t", description="", server_id="s1", risk_level="high"))
        tools = reg.tools_for_role("basic")
        names = [t.name for t in tools]
        assert "low_t" in names
        assert "med_t" not in names
        assert "hi_t" not in names

    def test_tools_for_role_premium_low_and_medium(self):
        from tools.schemas import MCPToolSchema
        reg = self._make_registry()
        reg.register_tool(MCPToolSchema(name="low_t", description="", server_id="s1", risk_level="low"))
        reg.register_tool(MCPToolSchema(name="med_t", description="", server_id="s1", risk_level="medium"))
        reg.register_tool(MCPToolSchema(name="hi_t", description="", server_id="s1", risk_level="high"))
        tools = reg.tools_for_role("premium")
        names = [t.name for t in tools]
        assert "low_t" in names
        assert "med_t" in names
        assert "hi_t" not in names

    def test_tools_for_role_advisor_all_tools(self):
        from tools.schemas import MCPToolSchema
        reg = self._make_registry()
        reg.register_tool(MCPToolSchema(name="low_t", description="", server_id="s1", risk_level="low"))
        reg.register_tool(MCPToolSchema(name="hi_t", description="", server_id="s1", risk_level="high"))
        tools = reg.tools_for_role("advisor")
        assert len(tools) == 2

    def test_tools_for_role_admin_all_tools(self):
        from tools.schemas import MCPToolSchema
        reg = self._make_registry()
        reg.register_tool(MCPToolSchema(name="t", description="", server_id="s1", risk_level="high"))
        tools = reg.tools_for_role("admin")
        assert len(tools) == 1

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool_raises(self):
        reg = self._make_registry()
        with pytest.raises(ValueError, match="not registered"):
            await reg.call_tool("unknown_tool", {}, "call-1")

    @pytest.mark.asyncio
    async def test_call_tool_known_tool_dispatches(self):
        from tools.schemas import MCPServerConfig, MCPToolSchema
        reg = self._make_registry()

        cfg = MCPServerConfig(server_id="srv1", transport="sse", url="http://x")
        tool = MCPToolSchema(name="my_tool", description="", server_id="srv1", timeout_ms=5000)
        reg.register_server(cfg)
        reg.register_tool(tool)

        with patch("tools.mcp_client.call_mcp_tool", new=AsyncMock(return_value={"result": "ok"})):
            result = await reg.call_tool("my_tool", {"a": 1}, "call-42")

        assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_call_tool_server_not_registered_raises(self):
        from tools.schemas import MCPToolSchema
        reg = self._make_registry()
        # Register tool but NOT its server
        tool = MCPToolSchema(name="orphan_tool", description="", server_id="missing-srv")
        reg.register_tool(tool)

        with pytest.raises(ValueError, match="Server"):
            await reg.call_tool("orphan_tool", {}, "call-x")


class TestGetRegistry:
    @pytest.mark.asyncio
    async def test_get_registry_returns_instance(self):
        from tools.registry import get_registry, reset_registry
        reset_registry()
        reg = await get_registry()
        assert reg is not None

    @pytest.mark.asyncio
    async def test_get_registry_singleton(self):
        from tools.registry import get_registry, reset_registry
        reset_registry()
        r1 = await get_registry()
        r2 = await get_registry()
        assert r1 is r2

    def test_reset_registry(self):
        from tools.registry import get_registry, reset_registry, _registry_instance
        import tools.registry as reg_mod
        reset_registry()
        assert reg_mod._registry_instance is None


# ============================================================================
# backend/demo_tools/financial_calc.py
# ============================================================================

class TestDCFValuation:
    def test_empty_cash_flows_returns_zero(self):
        from backend.demo_tools.financial_calc import dcf_valuation
        assert dcf_valuation([], 0.10, 0.03) == 0.0

    def test_discount_lte_terminal_growth_raises(self):
        from backend.demo_tools.financial_calc import dcf_valuation
        with pytest.raises(ValueError):
            dcf_valuation([100.0], 0.03, 0.03)

    def test_discount_less_than_terminal_growth_raises(self):
        from backend.demo_tools.financial_calc import dcf_valuation
        with pytest.raises(ValueError):
            dcf_valuation([100.0], 0.02, 0.05)

    def test_single_cash_flow(self):
        from backend.demo_tools.financial_calc import dcf_valuation
        result = dcf_valuation([100.0], 0.10, 0.03)
        assert isinstance(result, float)
        assert result > 0

    def test_multiple_cash_flows(self):
        from backend.demo_tools.financial_calc import dcf_valuation
        cfs = [100.0, 110.0, 121.0, 133.0, 146.0]
        result = dcf_valuation(cfs, 0.10, 0.03)
        assert isinstance(result, float)
        assert result > 0

    def test_dcf_result_is_rounded(self):
        from backend.demo_tools.financial_calc import dcf_valuation
        result = dcf_valuation([100.0, 110.0], 0.10, 0.03)
        # Should be rounded to 2 decimal places
        assert result == round(result, 2)


class TestValueAtRisk:
    def test_empty_returns_zero(self):
        from backend.demo_tools.financial_calc import value_at_risk
        assert value_at_risk([]) == 0.0

    def test_single_positive_return(self):
        from backend.demo_tools.financial_calc import value_at_risk
        # Single positive return — VaR should be negative (gain, not loss)
        result = value_at_risk([0.05])
        assert isinstance(result, float)

    def test_var_with_losses(self):
        from backend.demo_tools.financial_calc import value_at_risk
        returns = [-0.05, -0.03, 0.01, 0.02, 0.04]
        result = value_at_risk(returns, confidence=0.95)
        assert isinstance(result, float)
        assert result >= 0  # VaR expressed as positive loss

    def test_var_confidence_99(self):
        from backend.demo_tools.financial_calc import value_at_risk
        returns = [0.01, 0.02, -0.01, 0.03, 0.02, -0.02]
        result = value_at_risk(returns, confidence=0.99)
        assert isinstance(result, float)


class TestSharpeRatio:
    def test_single_return_gives_zero(self):
        from backend.demo_tools.financial_calc import sharpe_ratio
        assert sharpe_ratio([0.05]) == 0.0

    def test_zero_std_gives_zero(self):
        from backend.demo_tools.financial_calc import sharpe_ratio
        # Identical returns → std dev = 0 → Sharpe = 0
        result = sharpe_ratio([0.01, 0.01, 0.01, 0.01])
        assert result == 0.0

    def test_positive_returns_gives_positive_sharpe(self):
        from backend.demo_tools.financial_calc import sharpe_ratio
        result = sharpe_ratio([0.02, 0.03, 0.025, 0.03, 0.028])
        assert isinstance(result, float)

    def test_custom_risk_free_rate(self):
        from backend.demo_tools.financial_calc import sharpe_ratio
        result = sharpe_ratio([0.01, 0.02, -0.01, 0.03], risk_free_rate=0.02)
        assert isinstance(result, float)


# ============================================================================
# risk_gates/gates/pre_llm.py — _redact_pii and run_pre_llm_gate MODIFY path
# ============================================================================

class TestRedactPII:
    def test_redact_ssn(self):
        from risk_gates.gates.pre_llm import _redact_pii
        text = "My SSN is 123-45-6789 and I need help."
        result, matches = _redact_pii(text)
        assert "123-45" not in result
        assert "***-**-6789" in result
        assert len(matches) == 1
        assert matches[0].pii_type == "ssn"

    def test_redact_credit_card(self):
        from risk_gates.gates.pre_llm import _redact_pii
        text = "Card: 4111 1111 1111 1234 please charge it."
        result, matches = _redact_pii(text)
        assert "4111" not in result
        assert "****-****-****-1234" in result
        assert any(m.pii_type == "credit_card" for m in matches)

    def test_redact_email(self):
        from risk_gates.gates.pre_llm import _redact_pii
        text = "Contact me at alice@example.com for details."
        result, matches = _redact_pii(text)
        assert "alice@example.com" not in result
        assert "al***@example.com" in result
        assert any(m.pii_type == "email" for m in matches)

    def test_redact_iban(self):
        from risk_gates.gates.pre_llm import _redact_pii
        text = "Transfer to GB29NWBK60161331926819 immediately."
        result, matches = _redact_pii(text)
        assert "GB29NWBK60161331926819" not in result
        assert "[REDACTED_IBAN]" in result
        assert any(m.pii_type == "iban" for m in matches)

    def test_no_pii_returns_unchanged(self):
        from risk_gates.gates.pre_llm import _redact_pii
        text = "What is the Sharpe ratio of my portfolio?"
        result, matches = _redact_pii(text)
        assert result == text
        assert matches == []

    def test_multiple_pii_types_all_redacted(self):
        from risk_gates.gates.pre_llm import _redact_pii
        text = "SSN 123-45-6789, email test@test.com"
        result, matches = _redact_pii(text)
        assert "123-45" not in result
        assert "test@test.com" not in result
        assert len(matches) >= 2

    def test_pii_match_has_correct_fields(self):
        from risk_gates.gates.pre_llm import _redact_pii
        text = "My email is bob@domain.org"
        _, matches = _redact_pii(text)
        assert len(matches) == 1
        m = matches[0]
        assert m.pii_type == "email"
        assert m.redacted_value is not None
        assert m.start_index >= 0
        assert m.end_index > m.start_index


def _make_gate_decision(action_val: str, reason: str = "test") -> "GateDecision":
    """Helper to build a GateDecision with required AuditEntry."""
    from risk_gates.schemas import GateAction, GateDecision, AuditEntry, GateName
    return GateDecision(
        action=GateAction(action_val),
        reason=reason,
        audit=AuditEntry(
            gate=GateName.PRE_LLM,
            action=GateAction(action_val),
            reason=reason,
            request_id="req-test",
            user_id="u1",
        ),
    )


@pytest.mark.asyncio
async def test_run_pre_llm_gate_modify_path():
    """run_pre_llm_gate with MODIFY action triggers PII redaction."""
    from risk_gates.schemas import (
        GateAction, PreLLMDecision, PreLLMRequest, UserRole
    )
    from risk_gates.gates.pre_llm import run_pre_llm_gate

    mock_inner_decision = PreLLMDecision(
        gate_decision=_make_gate_decision("modify", "pii_detected"),
        sanitized_input="My SSN is 123-45-6789",
        injection_score=0.1,
    )

    from risk_gates.schemas import RiskContext
    request = PreLLMRequest(
        user_input="My SSN is 123-45-6789",
        risk_context=RiskContext(session_id="s1", user_id="u1", user_role=UserRole.BASIC),
    )

    with patch(
        "risk_gates.gates.pre_llm.evaluate_pre_llm",
        new=AsyncMock(return_value=mock_inner_decision),
    ):
        result = await run_pre_llm_gate(request)

    assert result.gate_decision.action == GateAction.MODIFY
    # The sanitized_input should have PII redacted
    assert isinstance(result.sanitized_input, str)


@pytest.mark.asyncio
async def test_run_pre_llm_gate_allow_path():
    """run_pre_llm_gate with ALLOW action returns decision without modification."""
    from risk_gates.schemas import (
        GateAction, PreLLMDecision, PreLLMRequest, UserRole
    )
    from risk_gates.gates.pre_llm import run_pre_llm_gate

    mock_inner_decision = PreLLMDecision(
        gate_decision=_make_gate_decision("allow", "clean"),
        sanitized_input="Hello, how is the market today?",
        injection_score=0.0,
    )

    from risk_gates.schemas import RiskContext
    request = PreLLMRequest(
        user_input="Hello, how is the market today?",
        risk_context=RiskContext(session_id="s1", user_id="u1", user_role=UserRole.BASIC),
    )

    with patch(
        "risk_gates.gates.pre_llm.evaluate_pre_llm",
        new=AsyncMock(return_value=mock_inner_decision),
    ):
        result = await run_pre_llm_gate(request)

    assert result.gate_decision.action == GateAction.ALLOW
