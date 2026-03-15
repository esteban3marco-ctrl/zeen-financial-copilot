"""Tests for post_llm gate Python-side logic (disclaimer injection)."""
from __future__ import annotations

import pytest
import respx
import httpx

from risk_gates.gates.post_llm import _DISCLAIMER, run_post_llm_gate
from risk_gates.schemas import (
    GateAction,
    PostLLMRequest,
    RiskContext,
    UserRole,
)


def _make_ctx(role: UserRole = UserRole.BASIC) -> RiskContext:
    return RiskContext(session_id="s1", user_id="u1", user_role=role)


@pytest.mark.asyncio
class TestRunPostLLMGate:
    @respx.mock
    async def test_disclaimer_injected_on_modify(self) -> None:
        respx.post("http://localhost:8181/v1/data/staq/gates/post_llm").mock(
            return_value=httpx.Response(
                200,
                json={"result": {"decision": {"action": "modify", "reason": "Disclaimer injection required"}}},
            )
        )
        ctx = _make_ctx()
        req = PostLLMRequest(
            llm_response="You should consider buying this fund.",
            risk_context=ctx,
            original_input="What should I invest in?",
        )
        result = await run_post_llm_gate(req)
        assert result.gate_decision.action == GateAction.MODIFY
        assert result.modified_response is not None
        assert _DISCLAIMER in result.modified_response
        assert "You should consider buying this fund." in result.modified_response

    @respx.mock
    async def test_no_modification_on_allow(self) -> None:
        respx.post("http://localhost:8181/v1/data/staq/gates/post_llm").mock(
            return_value=httpx.Response(
                200,
                json={"result": {"decision": {"action": "allow", "reason": "OK"}}},
            )
        )
        ctx = _make_ctx()
        req = PostLLMRequest(
            llm_response="Your balance is $1,234.56.",
            risk_context=ctx,
            original_input="What is my balance?",
        )
        result = await run_post_llm_gate(req)
        assert result.gate_decision.action == GateAction.ALLOW
        assert result.modified_response is None

    @respx.mock
    async def test_deny_passes_through(self) -> None:
        respx.post("http://localhost:8181/v1/data/staq/gates/post_llm").mock(
            return_value=httpx.Response(
                200,
                json={"result": {"decision": {"action": "deny", "reason": "Regulated advice blocked"}}},
            )
        )
        ctx = _make_ctx()
        req = PostLLMRequest(
            llm_response="Guaranteed 20% returns! Buy now!",
            risk_context=ctx,
            original_input="Give me investment advice.",
        )
        result = await run_post_llm_gate(req)
        assert result.gate_decision.action == GateAction.DENY
