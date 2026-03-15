"""Tests for user profile management (Supabase calls mocked)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from memory.schemas import UserProfile
from memory.user_profile import get_or_create_profile


@pytest.mark.asyncio
class TestGetOrCreateProfile:
    @patch("memory.user_profile._get_supabase_client")
    async def test_returns_existing_profile(self, mock_client_fn: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "user_id": "u1",
                "role": "premium",
                "compliance_jurisdiction": "US",
                "authorized_topics": ["budgeting"],
                "preferences": {},
                "total_sessions": 5,
                "total_messages": 100,
            }
        )
        mock_client_fn.return_value = mock_client

        profile = await get_or_create_profile("u1")
        assert profile.user_id == "u1"
        assert profile.role == "premium"
        assert profile.total_sessions == 5

    @patch("memory.user_profile._get_supabase_client")
    async def test_creates_default_profile_when_not_found(self, mock_client_fn: MagicMock) -> None:
        mock_client = MagicMock()
        # First call raises (user not found), second call for insert succeeds
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_client_fn.return_value = mock_client

        profile = await get_or_create_profile("new_user")
        assert profile.user_id == "new_user"

    @patch("memory.user_profile._get_supabase_client")
    async def test_missing_env_returns_default(self, mock_client_fn: MagicMock) -> None:
        mock_client_fn.side_effect = KeyError("SUPABASE_URL")
        profile = await get_or_create_profile("u1")
        assert profile.user_id == "u1"
        assert profile.role == "basic"
