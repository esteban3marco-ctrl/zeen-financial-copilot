"""Tests for MCPToolRegistry."""
from __future__ import annotations

import pytest

from tools.registry import MCPToolRegistry, get_registry, reset_registry
from tools.schemas import MCPServerConfig, MCPToolSchema


def _make_server(server_id: str = "test-server") -> MCPServerConfig:
    return MCPServerConfig(server_id=server_id, transport="stdio", command="test-mcp")


def _make_tool(name: str = "market_data_lookup", server_id: str = "test-server") -> MCPToolSchema:
    return MCPToolSchema(name=name, description="test tool", server_id=server_id, risk_level="low")


class TestMCPToolRegistry:
    def setup_method(self) -> None:
        reset_registry()

    def test_register_server(self) -> None:
        reg = MCPToolRegistry()
        reg.register_server(_make_server())
        assert reg.get_server("test-server") is not None

    def test_register_tool(self) -> None:
        reg = MCPToolRegistry()
        reg.register_server(_make_server())
        reg.register_tool(_make_tool())
        assert reg.get_tool("market_data_lookup") is not None

    def test_server_for_tool(self) -> None:
        reg = MCPToolRegistry()
        reg.register_server(_make_server())
        reg.register_tool(_make_tool())
        assert reg.server_for_tool("market_data_lookup") == "test-server"

    def test_server_for_unknown_tool_returns_none(self) -> None:
        reg = MCPToolRegistry()
        assert reg.server_for_tool("nonexistent") is None

    def test_all_tools(self) -> None:
        reg = MCPToolRegistry()
        reg.register_server(_make_server())
        reg.register_tool(_make_tool("tool_a"))
        reg.register_tool(_make_tool("tool_b"))
        assert len(reg.all_tools()) == 2

    def test_tools_for_basic_role_excludes_high_risk(self) -> None:
        reg = MCPToolRegistry()
        reg.register_server(_make_server())
        reg.register_tool(_make_tool("safe_tool"))
        reg.register_tool(
            MCPToolSchema(name="risky_tool", description="x", server_id="test-server", risk_level="high")
        )
        basic_tools = reg.tools_for_role("basic")
        names = [t.name for t in basic_tools]
        assert "safe_tool" in names
        assert "risky_tool" not in names

    def test_admin_gets_all_tools(self) -> None:
        reg = MCPToolRegistry()
        reg.register_server(_make_server())
        for risk in ["low", "medium", "high"]:
            reg.register_tool(
                MCPToolSchema(name=f"tool_{risk}", description="x", server_id="test-server", risk_level=risk)  # type: ignore[arg-type]
            )
        admin_tools = reg.tools_for_role("admin")
        assert len(admin_tools) == 3


@pytest.mark.asyncio
class TestGetRegistry:
    async def test_get_registry_returns_singleton(self) -> None:
        reset_registry()
        r1 = await get_registry()
        r2 = await get_registry()
        assert r1 is r2

    async def test_reset_registry_creates_fresh_instance(self) -> None:
        r1 = await get_registry()
        reset_registry()
        r2 = await get_registry()
        assert r1 is not r2
