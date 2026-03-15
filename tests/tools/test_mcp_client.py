"""Tests for MCP client — HTTP transport mocked with respx."""
from __future__ import annotations

import pytest
import respx
import httpx

from tools.mcp_client import _call_via_http
from tools.schemas import MCPServerConfig


def _make_http_config(url: str = "http://localhost:9000") -> MCPServerConfig:
    return MCPServerConfig(
        server_id="test-server",
        transport="streamable_http",
        url=url,
        timeout_ms=5_000,
        max_retries=1,
    )


@pytest.mark.asyncio
class TestCallViaHTTP:
    @respx.mock
    async def test_successful_http_call(self) -> None:
        respx.post("http://localhost:9000/tools/call").mock(
            return_value=httpx.Response(200, json={"result": {"price": 150.25}})
        )
        config = _make_http_config()
        result = await _call_via_http(config, "market_data_lookup", {"ticker": "AAPL"})
        assert result == {"price": 150.25}

    @respx.mock
    async def test_server_error_raises(self) -> None:
        respx.post("http://localhost:9000/tools/call").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        config = _make_http_config()
        with pytest.raises(httpx.HTTPStatusError):
            await _call_via_http(config, "market_data_lookup", {"ticker": "AAPL"})

    async def test_missing_url_raises_value_error(self) -> None:
        config = MCPServerConfig(
            server_id="s1", transport="streamable_http", url=None
        )
        with pytest.raises(ValueError, match="url"):
            await _call_via_http(config, "tool", {})
