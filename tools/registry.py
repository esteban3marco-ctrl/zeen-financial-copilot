"""MCPToolRegistry: discover, register, and lookup MCP tools."""
from __future__ import annotations

import logging
from typing import Any

from tools.schemas import MCPServerConfig, MCPToolSchema

logger = logging.getLogger(__name__)

_registry_instance: "MCPToolRegistry | None" = None


class MCPToolRegistry:
    """Central registry of all available MCP tools across all servers."""

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerConfig] = {}
        self._tools: dict[str, MCPToolSchema] = {}
        self._tool_server_map: dict[str, str] = {}

    def register_server(self, config: MCPServerConfig) -> None:
        self._servers[config.server_id] = config
        logger.info("Registered MCP server: %s (%s)", config.server_id, config.transport)

    def register_tool(self, tool: MCPToolSchema) -> None:
        self._tools[tool.name] = tool
        self._tool_server_map[tool.name] = tool.server_id
        logger.debug("Registered tool: %s -> %s", tool.name, tool.server_id)

    def get_tool(self, tool_name: str) -> MCPToolSchema | None:
        return self._tools.get(tool_name)

    def get_server(self, server_id: str) -> MCPServerConfig | None:
        return self._servers.get(server_id)

    def server_for_tool(self, tool_name: str) -> str | None:
        return self._tool_server_map.get(tool_name)

    def all_tools(self) -> list[MCPToolSchema]:
        return list(self._tools.values())

    def tools_for_role(self, role: str) -> list[MCPToolSchema]:
        """Filter tools by risk level appropriate for role."""
        if role in {"advisor", "admin"}:
            return self.all_tools()
        if role == "premium":
            return [t for t in self.all_tools() if t.risk_level in {"low", "medium"}]
        return [t for t in self.all_tools() if t.risk_level == "low"]

    async def call_tool(
        self, tool_name: str, params: dict[str, Any], call_id: str
    ) -> Any:
        """Dispatch a tool call to the appropriate MCP server."""
        from tools.mcp_client import call_mcp_tool  # lazy import

        server_id = self.server_for_tool(tool_name)
        if server_id is None:
            raise ValueError(f"Tool '{tool_name}' not registered in registry")

        server_config = self.get_server(server_id)
        if server_config is None:
            raise ValueError(f"Server '{server_id}' not registered in registry")

        tool_schema = self.get_tool(tool_name)
        timeout_ms = tool_schema.timeout_ms if tool_schema else server_config.timeout_ms

        return await call_mcp_tool(
            server_config=server_config,
            tool_name=tool_name,
            params=params,
            call_id=call_id,
            timeout_ms=timeout_ms,
        )


async def get_registry() -> MCPToolRegistry:
    """Get or initialize the global tool registry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = MCPToolRegistry()
    return _registry_instance


def reset_registry() -> None:
    """Reset registry (used in tests)."""
    global _registry_instance
    _registry_instance = None
