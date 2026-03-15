"""Tests for conversation memory (Supabase calls mocked)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent_runtime.state import TraceMetadata
from memory.conversation import _message_to_record, persist_turn
from memory.schemas import MessageRecord


class TestMessageToRecord:
    def test_human_message(self) -> None:
        record = _message_to_record(HumanMessage(content="hello"), sequence_num=0)
        assert record.role == "human"
        assert record.content == "hello"
        assert record.sequence_num == 0

    def test_ai_message(self) -> None:
        record = _message_to_record(AIMessage(content="Hi there"), sequence_num=1)
        assert record.role == "ai"
        assert record.sequence_num == 1

    def test_gate_decisions_attached(self) -> None:
        gate_dict = {"pre_llm": {"action": "allow", "reason": "ok"}}
        record = _message_to_record(HumanMessage(content="x"), sequence_num=0, gate_decisions=gate_dict)
        assert record.gate_decisions == gate_dict


@pytest.mark.asyncio
class TestPersistTurn:
    @patch("memory.conversation._get_supabase_client")
    async def test_persist_calls_supabase(self, mock_client_fn: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": "conv-123"}
        )
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_client_fn.return_value = mock_client

        await persist_turn(
            session_id="s1",
            user_id="u1",
            messages=[HumanMessage(content="hello"), AIMessage(content="hi")],
            gate_decisions={},
            metadata=TraceMetadata(tokens_total=50),
        )

        assert mock_client.table.called

    @patch("memory.conversation._get_supabase_client")
    async def test_missing_env_vars_does_not_raise(self, mock_client_fn: MagicMock) -> None:
        mock_client_fn.side_effect = KeyError("SUPABASE_URL")
        # Should log warning, not raise
        await persist_turn(
            session_id="s1",
            user_id="u1",
            messages=[],
            gate_decisions={},
            metadata=TraceMetadata(),
        )
