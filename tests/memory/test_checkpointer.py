"""Tests for SupabaseCheckpointer."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from memory.checkpointer import SupabaseCheckpointer


class TestSupabaseCheckpointer:
    def _make_config(self, thread_id: str = "session-001") -> dict:
        return {"configurable": {"thread_id": thread_id}}

    @patch("memory.checkpointer._get_supabase_client")
    def test_get_returns_none_when_no_checkpoint(self, mock_client_fn: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"checkpoint": None}
        )
        mock_client_fn.return_value = mock_client

        saver = SupabaseCheckpointer()
        result = saver.get(self._make_config())
        assert result is None

    @patch("memory.checkpointer._get_supabase_client")
    def test_get_returns_none_on_exception(self, mock_client_fn: MagicMock) -> None:
        mock_client_fn.side_effect = KeyError("SUPABASE_URL")
        saver = SupabaseCheckpointer()
        result = saver.get(self._make_config())
        assert result is None

    @patch("memory.checkpointer._get_supabase_client")
    def test_put_returns_config(self, mock_client_fn: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        mock_client_fn.return_value = mock_client

        saver = SupabaseCheckpointer()
        config = self._make_config()
        result = saver.put(config, {}, {})  # type: ignore[arg-type]
        assert result == config

    @patch("memory.checkpointer._get_supabase_client")
    def test_put_does_not_raise_on_db_error(self, mock_client_fn: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value.execute.side_effect = RuntimeError("DB error")
        mock_client_fn.return_value = mock_client

        saver = SupabaseCheckpointer()
        # Should not raise
        result = saver.put(self._make_config(), {}, {})  # type: ignore[arg-type]
        assert result is not None

    def test_list_returns_empty_iterator(self) -> None:
        saver = SupabaseCheckpointer()
        result = list(saver.list(None))
        assert result == []
