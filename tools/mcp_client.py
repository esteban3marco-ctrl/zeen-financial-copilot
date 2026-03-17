"""MCP client wrapper: connect to servers, call tools, handle transports."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from tools.schemas import MCPServerConfig

logger = logging.getLogger(__name__)

_DEFAULT_RETRY_DELAYS = [1.0, 2.0]


async def list_mcp_tools(server_config: MCPServerConfig) -> list[MCPToolSchema]:
    """Connect to MCP server and return list of available tools."""
    from tools.schemas import MCPToolParam, MCPToolSchema

    if server_config.transport == "stdio":
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        if server_config.command is None:
            raise ValueError(f"stdio transport requires 'command' for server {server_config.server_id}")

        cmd_parts = server_config.command.split()
        server_params = StdioServerParameters(
            command=cmd_parts[0],
            args=cmd_parts[1:],
            env=server_config.env or None,
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.list_tools()
                
                tools = []
                for t in response.tools:
                    # Convert MCP SDK tool to our schema
                    params = []
                    # Simple mapping for internal schema - in production we'd parse JSON Schema
                    # This is a simplification for the demo architecture
                    input_schema = getattr(t, "inputSchema", {})
                    props = input_schema.get("properties", {})
                    required = input_schema.get("required", [])
                    
                    for name, p in props.items():
                        params.append(MCPToolParam(
                            name=name,
                            type=p.get("type", "string"),
                            description=p.get("description", ""),
                            required=name in required
                        ))
                    
                    tools.append(MCPToolSchema(
                        name=t.name,
                        description=t.description or "",
                        server_id=server_config.server_id,
                        parameters=params,
                        # Metadata can be passed via tool name or description patterns in this architecture
                        requires_sandbox="sandbox" in (t.description or "").lower(),
                        risk_level="high" if "trade" in t.name.lower() else "low"
                    ))
                return tools
    
    # For HTTP/SSE discovery
    if server_config.transport in {"sse", "streamable_http"}:
        import httpx
        async with httpx.AsyncClient(timeout=server_config.timeout_ms / 1000) as client:
            response = await client.get(f"{server_config.url}/tools")
            response.raise_for_status()
            raw_tools = response.json().get("tools", [])
            return [MCPToolSchema(**t) for t in raw_tools]

    raise ValueError(f"Unsupported discovery transport: {server_config.transport}")


async def call_mcp_tool(
    server_config: MCPServerConfig,
    tool_name: str,
    params: dict[str, Any],
    call_id: str,
    timeout_ms: int = 30_000,
) -> Any:
    """
    Call a tool on an MCP server with retry and timeout.
    Supports stdio, sse, and streamable_http transports.
    """
    timeout_s = timeout_ms / 1000.0
    last_exc: Exception | None = None

    for attempt in range(server_config.max_retries + 1):
        try:
            result = await asyncio.wait_for(
                _dispatch_call(server_config, tool_name, params, call_id),
                timeout=timeout_s,
            )
            logger.debug(
                "MCP call success: tool=%s server=%s attempt=%d",
                tool_name, server_config.server_id, attempt,
            )
            return result
        except asyncio.TimeoutError:
            raise  # Timeout is not retried
        except ConnectionError as exc:
            last_exc = exc
            if attempt < server_config.max_retries:
                delay = _DEFAULT_RETRY_DELAYS[min(attempt, len(_DEFAULT_RETRY_DELAYS) - 1)]
                logger.warning(
                    "MCP connection error (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1, server_config.max_retries + 1, exc, delay,
                )
                await asyncio.sleep(delay)

    raise ConnectionError(
        f"MCP tool '{tool_name}' failed after {server_config.max_retries + 1} attempts"
    ) from last_exc


async def _dispatch_call(
    config: MCPServerConfig,
    tool_name: str,
    params: dict[str, Any],
    call_id: str,
) -> Any:
    """Inner dispatch based on transport type."""
    if config.transport == "stdio":
        return await _call_via_stdio(config, tool_name, params)
    if config.transport in {"sse", "streamable_http"}:
        return await _call_via_http(config, tool_name, params)
    raise ValueError(f"Unsupported MCP transport: {config.transport}")


async def _call_via_stdio(
    config: MCPServerConfig,
    tool_name: str,
    params: dict[str, Any],
) -> Any:
    """Call MCP tool via stdio transport using mcp SDK."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    if config.command is None:
        raise ValueError(f"stdio transport requires 'command' for server {config.server_id}")

    cmd_parts = config.command.split()
    server_params = StdioServerParameters(
        command=cmd_parts[0],
        args=cmd_parts[1:],
        env=config.env or None,
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, params)
            return result.content


async def _call_via_http(
    config: MCPServerConfig,
    tool_name: str,
    params: dict[str, Any],
) -> Any:
    """Call MCP tool via SSE or streamable HTTP transport."""
    import httpx

    if config.url is None:
        raise ValueError(f"HTTP transport requires 'url' for server {config.server_id}")

    async with httpx.AsyncClient(timeout=config.timeout_ms / 1000) as client:
        response = await client.post(
            f"{config.url}/tools/call",
            json={"name": tool_name, "arguments": params},
        )
        response.raise_for_status()
        return response.json().get("result")
