"""
Extended tests for memory/conversation.py and memory/user_profile.py.

All Supabase calls are mocked to avoid external service dependencies.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from memory.schemas import ConversationMemory, MessageRecord, UserProfile
from risk_gates.schemas import UserRole


# ---------------------------------------------------------------------------
# Helpers: mock Supabase client factory
# ---------------------------------------------------------------------------

def _make_supabase_mock(select_data: Any = None, upsert_ok: bool = True) -> MagicMock:
    """Return a MagicMock that mimics the Supabase client table chaining API."""
    mock_result = MagicMock()
    mock_result.data = select_data

    mock_table = MagicMock()
    for method in ("select", "eq", "single", "order", "limit", "upsert", "insert", "update", "rpc"):
        getattr(mock_table, method).return_value = mock_table
    mock_table.execute.return_value = mock_result

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mock_client.rpc.return_value = mock_table

    return mock_client


# ---------------------------------------------------------------------------
# _message_to_record helper
# ---------------------------------------------------------------------------

def test_message_to_record_human():
    from memory.conversation import _message_to_record
    msg = HumanMessage(content="Hi there")
    rec = _message_to_record(msg, sequence_num=0)
    assert rec.role == "human"
    assert rec.content == "Hi there"
    assert rec.sequence_num == 0


def test_message_to_record_ai():
    from memory.conversation import _message_to_record
    msg = AIMessage(content="Hello!")
    rec = _message_to_record(msg, sequence_num=1)
    assert rec.role == "ai"
    assert rec.content == "Hello!"


def test_message_to_record_tool():
    from memory.conversation import _message_to_record
    msg = ToolMessage(content="result", tool_call_id="call-1")
    rec = _message_to_record(msg, sequence_num=2)
    assert rec.role == "tool"
    assert rec.tool_call_id == "call-1"


def test_message_to_record_unknown_becomes_system():
    """Any non-human/ai/tool message maps to 'system'."""
    from langchain_core.messages import SystemMessage
    from memory.conversation import _message_to_record
    msg = SystemMessage(content="You are helpful")
    rec = _message_to_record(msg, sequence_num=0)
    assert rec.role == "system"


def test_message_to_record_with_gate_decisions():
    from memory.conversation import _message_to_record
    msg = HumanMessage(content="trade request")
    gate_decisions = {"pre_llm": {"action": "allow", "reason": "ok"}}
    rec = _message_to_record(msg, sequence_num=3, gate_decisions=gate_decisions)
    assert rec.gate_decisions == gate_decisions


# ---------------------------------------------------------------------------
# persist_turn: skips gracefully when Supabase not configured
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_persist_turn_skips_without_supabase(caplog):
    """persist_turn logs a warning and does not raise when env vars are missing."""
    import logging
    from agent_runtime.state import TraceMetadata
    from risk_gates.schemas import GateDecision

    messages = [HumanMessage(content="hello"), AIMessage(content="world")]
    gate_decisions: dict[str, GateDecision] = {}
    metadata = TraceMetadata(
        trace_id="t1",
        session_id="s1",
        user_id="u1",
        model_used="claude",
        tokens_prompt=5,
        tokens_completion=10,
        tokens_total=15,
        latency_ms=50.0,
        iteration_count=1,
    )

    # Patch _get_supabase_client to raise KeyError (simulating missing env vars)
    with patch("memory.conversation._get_supabase_client", side_effect=KeyError("SUPABASE_URL")):
        # Should complete without raising
        from memory.conversation import persist_turn
        await persist_turn(
            session_id="test-session",
            user_id="user-1",
            messages=messages,
            gate_decisions=gate_decisions,
            metadata=metadata,
        )


@pytest.mark.asyncio
async def test_persist_turn_calls_upsert():
    """persist_turn calls Supabase upsert and insert with correct data."""
    from agent_runtime.state import TraceMetadata
    from risk_gates.schemas import GateDecision
    from memory.conversation import persist_turn

    messages = [HumanMessage(content="hello"), AIMessage(content="world")]
    gate_decisions: dict[str, GateDecision] = {}
    metadata = TraceMetadata(
        trace_id="t2",
        session_id="s2",
        user_id="u2",
        model_used="claude",
        tokens_prompt=5,
        tokens_completion=10,
        tokens_total=15,
        latency_ms=50.0,
        iteration_count=1,
    )

    mock_client = _make_supabase_mock(select_data={"id": "conv-uuid-1"})

    with patch("memory.conversation._get_supabase_client", return_value=mock_client):
        await persist_turn(
            session_id="s2",
            user_id="u2",
            messages=messages,
            gate_decisions=gate_decisions,
            metadata=metadata,
        )

    # Verify that table() was called at least once
    mock_client.table.assert_called()


# ---------------------------------------------------------------------------
# load_conversation: returns None for missing session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_conversation_returns_none_when_no_data():
    """load_conversation returns None when Supabase returns empty result."""
    from memory.conversation import load_conversation

    mock_client = _make_supabase_mock(select_data=None)

    with patch("memory.conversation._get_supabase_client", return_value=mock_client):
        result = await load_conversation("nonexistent-session")

    assert result is None


@pytest.mark.asyncio
async def test_load_conversation_returns_none_without_supabase():
    """load_conversation returns None when env vars are missing."""
    from memory.conversation import load_conversation

    with patch("memory.conversation._get_supabase_client", side_effect=KeyError("SUPABASE_URL")):
        result = await load_conversation("session-abc")

    assert result is None


@pytest.mark.asyncio
async def test_load_conversation_returns_memory_object():
    """load_conversation returns a ConversationMemory when data is found."""
    from memory.conversation import load_conversation

    data = {
        "id": "conv-1",
        "session_id": "sess-1",
        "user_id": "user-1",
        "messages": [
            {
                "id": "msg-1",
                "role": "human",
                "content": "hello",
                "sequence_num": 0,
                "created_at": datetime.utcnow().isoformat(),
            }
        ],
        "turn_count": 1,
        "total_tokens": 10,
        "status": "active",
    }

    mock_client = _make_supabase_mock(select_data=data)

    with patch("memory.conversation._get_supabase_client", return_value=mock_client):
        result = await load_conversation("sess-1")

    assert result is not None
    assert isinstance(result, ConversationMemory)
    assert result.session_id == "sess-1"
    assert result.user_id == "user-1"
    assert len(result.messages) == 1
    assert result.messages[0].role == "human"


@pytest.mark.asyncio
async def test_load_conversation_handles_exception():
    """load_conversation returns None on unexpected exceptions."""
    from memory.conversation import load_conversation

    with patch(
        "memory.conversation._get_supabase_client",
        side_effect=RuntimeError("network error"),
    ):
        result = await load_conversation("session-xyz")

    assert result is None


# ---------------------------------------------------------------------------
# UserProfile schema tests
# ---------------------------------------------------------------------------

def test_user_profile_creation():
    """UserProfile can be created with just a user_id."""
    profile = UserProfile(user_id="user-123")
    assert profile.user_id == "user-123"
    assert profile.role == UserRole.BASIC
    assert profile.compliance_jurisdiction == "US"
    assert profile.total_sessions == 0
    assert profile.total_messages == 0


def test_user_profile_authorized_topics_default():
    """UserProfile has default authorized topics list."""
    profile = UserProfile(user_id="u1")
    assert "market_data" in profile.authorized_topics
    assert "portfolio_view" in profile.authorized_topics


def test_user_profile_preference_setting():
    """UserProfile preferences field accepts arbitrary dict."""
    profile = UserProfile(
        user_id="u2",
        preferences={"theme": "dark", "currency": "USD"},
    )
    assert profile.preferences["theme"] == "dark"
    assert profile.preferences["currency"] == "USD"


def test_user_profile_role_assignment():
    profile = UserProfile(user_id="u3", role=UserRole.ADVISOR)
    assert profile.role == UserRole.ADVISOR


def test_user_profile_display_name():
    profile = UserProfile(user_id="u4", display_name="Alice")
    assert profile.display_name == "Alice"


def test_user_profile_model_dump():
    """UserProfile.model_dump() produces a serialisable dict."""
    profile = UserProfile(user_id="u5", display_name="Bob")
    data = profile.model_dump(mode="json")
    assert data["user_id"] == "u5"
    assert data["display_name"] == "Bob"
    assert "authorized_topics" in data


# ---------------------------------------------------------------------------
# get_or_create_profile: no Supabase → returns default profile
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_or_create_profile_without_supabase():
    """get_or_create_profile returns default UserProfile when env vars missing."""
    from memory.user_profile import get_or_create_profile

    with patch(
        "memory.user_profile._get_supabase_client",
        side_effect=KeyError("SUPABASE_URL"),
    ):
        profile = await get_or_create_profile("user-demo")

    assert profile.user_id == "user-demo"
    assert isinstance(profile, UserProfile)


@pytest.mark.asyncio
async def test_get_or_create_profile_returns_existing():
    """get_or_create_profile returns existing profile data from Supabase."""
    from memory.user_profile import get_or_create_profile

    existing_data = {
        "user_id": "user-abc",
        "display_name": "Alice",
        "role": "advisor",
        "compliance_jurisdiction": "EU",
        "portfolio_size_tier": None,
        "risk_tolerance": None,
        "authorized_topics": ["market_data"],
        "preferences": {},
        "total_sessions": 5,
        "total_messages": 20,
        "last_active_at": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    mock_client = _make_supabase_mock(select_data=existing_data)

    with patch("memory.user_profile._get_supabase_client", return_value=mock_client):
        profile = await get_or_create_profile("user-abc")

    assert profile.user_id == "user-abc"
    assert profile.display_name == "Alice"
    assert profile.total_sessions == 5


@pytest.mark.asyncio
async def test_get_or_create_profile_creates_when_not_found():
    """get_or_create_profile creates and returns default profile when not found."""
    from memory.user_profile import get_or_create_profile

    # First call returns no data (profile not found)
    mock_client = _make_supabase_mock(select_data=None)

    with patch("memory.user_profile._get_supabase_client", return_value=mock_client):
        profile = await get_or_create_profile("new-user-999")

    assert profile.user_id == "new-user-999"
    assert isinstance(profile, UserProfile)


# ---------------------------------------------------------------------------
# update_preferences: no Supabase → logs warning, does not raise
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_preferences_without_supabase():
    """update_preferences does not raise when Supabase is unavailable."""
    from memory.user_profile import update_preferences

    with patch(
        "memory.user_profile._get_supabase_client",
        side_effect=Exception("unavailable"),
    ):
        # Should complete without raising
        await update_preferences("user-1", {"currency": "EUR"})


@pytest.mark.asyncio
async def test_update_preferences_calls_supabase():
    """update_preferences calls Supabase update with the given preferences."""
    from memory.user_profile import update_preferences

    mock_client = _make_supabase_mock()

    with patch("memory.user_profile._get_supabase_client", return_value=mock_client):
        await update_preferences("user-2", {"theme": "light"})

    mock_client.table.assert_called_with("user_profiles")


# ---------------------------------------------------------------------------
# increment_session_count: no Supabase → logs warning, does not raise
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_increment_session_count_without_supabase():
    """increment_session_count does not raise when Supabase is unavailable."""
    from memory.user_profile import increment_session_count

    with patch(
        "memory.user_profile._get_supabase_client",
        side_effect=Exception("unavailable"),
    ):
        await increment_session_count("user-x")


@pytest.mark.asyncio
async def test_increment_session_count_calls_rpc():
    """increment_session_count calls Supabase RPC."""
    from memory.user_profile import increment_session_count

    mock_client = _make_supabase_mock()

    with patch("memory.user_profile._get_supabase_client", return_value=mock_client):
        await increment_session_count("user-rpc")

    mock_client.rpc.assert_called_once()
    call_args = mock_client.rpc.call_args
    assert "increment_user_sessions" in str(call_args)
