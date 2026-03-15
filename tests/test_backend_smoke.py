"""
Backend smoke tests for Financial Copilot.

Tests basic imports and instantiation of key backend modules and schemas.
"""
from __future__ import annotations

import pytest
from datetime import datetime

# Import tests
def test_import_config():
    """Test that backend.config.Settings can be imported."""
    from backend.config import Settings
    assert Settings is not None


def test_import_chat_schemas():
    """Test that chat schemas can be imported."""
    from backend.schemas.chat import ChatRequest, ChatResponse
    assert ChatRequest is not None
    assert ChatResponse is not None


def test_import_gate_event():
    """Test that GateEventOut can be imported."""
    from backend.schemas.gate_event import GateEventOut
    assert GateEventOut is not None


def test_import_tool_event():
    """Test that ToolEventOut can be imported."""
    from backend.schemas.tool_event import ToolEventOut
    assert ToolEventOut is not None


def test_import_websocket_protocol():
    """Test that all WebSocket message types can be imported."""
    from backend.websocket.protocol import (
        WSConnected,
        WSTurnStart,
        WSToken,
        WSGateEvent,
        WSToolStart,
        WSToolResult,
        WSTurnEnd,
        WSError,
        WSPing,
        WSPong,
        WSServerMessage,
        WSChatMessage,
        WSClientPing,
        WSClientMessage,
    )
    assert WSConnected is not None
    assert WSTurnStart is not None
    assert WSToken is not None
    assert WSGateEvent is not None
    assert WSToolStart is not None
    assert WSToolResult is not None
    assert WSTurnEnd is not None
    assert WSError is not None
    assert WSPing is not None
    assert WSPong is not None
    assert WSServerMessage is not None
    assert WSChatMessage is not None
    assert WSClientPing is not None
    assert WSClientMessage is not None


def test_import_financial_calc():
    """Test that financial calculation functions can be imported."""
    from backend.demo_tools.financial_calc import sharpe_ratio, value_at_risk, dcf_valuation
    assert sharpe_ratio is not None
    assert value_at_risk is not None
    assert dcf_valuation is not None


# Financial calculation tests
def test_sharpe_ratio():
    """Test sharpe_ratio function returns a float."""
    from backend.demo_tools.financial_calc import sharpe_ratio

    result = sharpe_ratio([0.01, 0.02, -0.01, 0.03, 0.02])
    assert isinstance(result, float)
    assert result >= 0.0


def test_value_at_risk():
    """Test value_at_risk function returns a float."""
    from backend.demo_tools.financial_calc import value_at_risk

    result = value_at_risk([0.01, 0.02, -0.01, 0.03, 0.02])
    assert isinstance(result, float)
    assert result >= 0.0


# Schema instantiation tests
def test_chat_request_creation():
    """Test ChatRequest can be instantiated."""
    from backend.schemas.chat import ChatRequest

    request = ChatRequest(message="test")
    assert request.message == "test"
    assert request.session_id is None
    assert request.user_role is not None


def test_gate_event_creation():
    """Test GateEventOut can be instantiated."""
    from backend.schemas.gate_event import GateEventOut

    now = datetime.now()
    event = GateEventOut(
        gate="pre_llm",
        action="allow",
        reason="ok",
        fired_at=now,
    )
    assert event.gate == "pre_llm"
    assert event.action == "allow"
    assert event.reason == "ok"
    assert event.fired_at == now
    assert event.metadata == {}


def test_tool_event_creation():
    """Test ToolEventOut can be instantiated."""
    from backend.schemas.tool_event import ToolEventOut

    event = ToolEventOut(
        tool_name="calculator",
        call_id="call_001",
        status="success",
        sandbox_used=False,
        execution_time_ms=100.5,
    )
    assert event.tool_name == "calculator"
    assert event.call_id == "call_001"
    assert event.status == "success"
    assert event.sandbox_used is False
    assert event.execution_time_ms == 100.5


def test_websocket_gate_event_creation():
    """Test WSGateEvent can be instantiated."""
    from backend.websocket.protocol import WSGateEvent

    event = WSGateEvent(
        gate="post_llm",
        action="deny",
        reason="risky",
        metadata={"risk_score": 0.9},
    )
    assert event.type == "gate_event"
    assert event.gate == "post_llm"
    assert event.action == "deny"
    assert event.reason == "risky"
    assert event.metadata == {"risk_score": 0.9}


def test_websocket_tool_start_creation():
    """Test WSToolStart can be instantiated."""
    from backend.websocket.protocol import WSToolStart

    msg = WSToolStart(
        tool_name="calc",
        call_id="123",
        params_preview={"x": 5},
    )
    assert msg.type == "tool_start"
    assert msg.tool_name == "calc"
    assert msg.call_id == "123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
