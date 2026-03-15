"""Tests for E2B sandbox wrapper."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.sandbox import _execute_sandbox, run_in_sandbox
from tools.schemas import SANDBOX_LIMITS_BY_ROLE, SandboxRequest, SandboxResourceLimits


class TestSandboxLimits:
    def test_all_roles_have_limits(self) -> None:
        for role in ["anonymous", "basic", "premium", "advisor", "admin"]:
            assert role in SANDBOX_LIMITS_BY_ROLE

    def test_admin_has_highest_memory(self) -> None:
        admin = SANDBOX_LIMITS_BY_ROLE["admin"]
        basic = SANDBOX_LIMITS_BY_ROLE["basic"]
        assert admin.memory_mb > basic.memory_mb

    def test_admin_network_enabled(self) -> None:
        assert SANDBOX_LIMITS_BY_ROLE["admin"].network_enabled is True
        assert SANDBOX_LIMITS_BY_ROLE["basic"].network_enabled is False


@pytest.mark.asyncio
class TestRunInSandbox:
    async def test_missing_api_key_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("E2B_API_KEY", raising=False)
        result = await run_in_sandbox(
            call_id="c1",
            tool_name="code_execute",
            code="print('hello')",
        )
        assert result.status == "error"
        assert "E2B_API_KEY" in result.stderr

    @patch("tools.sandbox.AsyncSandbox")
    async def test_successful_execution(self, mock_sandbox_cls: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("E2B_API_KEY", "test-key")

        mock_execution = MagicMock()
        mock_execution.results = ["42"]
        mock_execution.error = None

        mock_sandbox = AsyncMock()
        mock_sandbox.run_code = AsyncMock(return_value=mock_execution)
        mock_sandbox.__aenter__ = AsyncMock(return_value=mock_sandbox)
        mock_sandbox.__aexit__ = AsyncMock(return_value=None)
        mock_sandbox_cls.return_value = mock_sandbox

        result = await run_in_sandbox(
            call_id="c1",
            tool_name="code_execute",
            code="print(42)",
            language="python",
            user_role="basic",
        )

        assert result.status == "success"
        assert result.exit_code == 0
        assert "42" in result.stdout

    @patch("tools.sandbox.AsyncSandbox")
    async def test_timeout_returns_timeout_status(self, mock_sandbox_cls: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("E2B_API_KEY", "test-key")

        mock_sandbox = AsyncMock()
        mock_sandbox.run_code = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_sandbox.__aenter__ = AsyncMock(return_value=mock_sandbox)
        mock_sandbox.__aexit__ = AsyncMock(return_value=None)
        mock_sandbox_cls.return_value = mock_sandbox

        result = await run_in_sandbox(
            call_id="c1",
            tool_name="code_execute",
            code="import time; time.sleep(100)",
        )
        assert result.status == "timeout"
        assert result.exit_code == 124
