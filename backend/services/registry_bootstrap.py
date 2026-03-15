"""Bootstrap the MCP tool registry at application startup."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from tools.registry import MCPToolRegistry

logger = logging.getLogger(__name__)


async def bootstrap_registry(registry: MCPToolRegistry) -> None:
    """Register all demo MCP tools with the global registry."""
    try:
        from tools.schemas import MCPServerConfig, MCPToolParam, MCPToolSchema
    except ImportError:
        logger.warning("tools.schemas not available — skipping registry bootstrap")
        return

    demo_tools_dir = Path(__file__).parent.parent / "demo_tools"

    # ── Portfolio server (stdio) ───────────────────────────────────────
    portfolio_server = MCPServerConfig(
        server_id="demo_portfolio",
        transport="stdio",
        command=f"{sys.executable} {demo_tools_dir / 'portfolio.py'}",
        timeout_ms=15_000,
    )
    registry.register_server(portfolio_server)

    registry.register_tool(
        MCPToolSchema(
            name="get_portfolio",
            description="Retrieve the user's current portfolio summary including total value, asset allocation, and performance metrics.",
            server_id="demo_portfolio",
            parameters=[
                MCPToolParam(name="user_id", type="string", description="User identifier", required=True),
            ],
            requires_sandbox=False,
            risk_level="low",
        )
    )
    registry.register_tool(
        MCPToolSchema(
            name="get_holdings",
            description="List individual holdings in the portfolio, optionally filtered by symbol.",
            server_id="demo_portfolio",
            parameters=[
                MCPToolParam(name="user_id", type="string", description="User identifier", required=True),
                MCPToolParam(name="symbol", type="string", description="Filter by ticker symbol (optional)", required=False),
            ],
            requires_sandbox=False,
            risk_level="low",
        )
    )

    # ── Market data server (stdio) ─────────────────────────────────────
    market_server = MCPServerConfig(
        server_id="demo_market_data",
        transport="stdio",
        command=f"{sys.executable} {demo_tools_dir / 'market_data.py'}",
        timeout_ms=10_000,
    )
    registry.register_server(market_server)

    registry.register_tool(
        MCPToolSchema(
            name="get_quote",
            description="Get the latest stock quote for a given ticker symbol.",
            server_id="demo_market_data",
            parameters=[
                MCPToolParam(name="symbol", type="string", description="Ticker symbol (e.g. AAPL)", required=True),
            ],
            requires_sandbox=False,
            risk_level="low",
        )
    )
    registry.register_tool(
        MCPToolSchema(
            name="get_market_summary",
            description="Get a high-level summary of major market indices and sector performance.",
            server_id="demo_market_data",
            parameters=[],
            requires_sandbox=False,
            risk_level="low",
        )
    )

    # ── Financial calc (sandbox required) ─────────────────────────────
    calc_server = MCPServerConfig(
        server_id="demo_financial_calc",
        transport="stdio",
        command=f"{sys.executable} {demo_tools_dir / 'financial_calc.py'}",
        timeout_ms=60_000,
    )
    registry.register_server(calc_server)

    registry.register_tool(
        MCPToolSchema(
            name="sharpe_ratio",
            description="Calculate the Sharpe ratio for a series of portfolio returns.",
            server_id="demo_financial_calc",
            parameters=[
                MCPToolParam(name="returns", type="array", description="List of period returns as floats", required=True),
                MCPToolParam(name="risk_free_rate", type="number", description="Annual risk-free rate (default 0.05)", required=False),
            ],
            requires_sandbox=True,
            risk_level="low",
        )
    )
    registry.register_tool(
        MCPToolSchema(
            name="value_at_risk",
            description="Calculate Value at Risk (VaR) at a given confidence level.",
            server_id="demo_financial_calc",
            parameters=[
                MCPToolParam(name="returns", type="array", description="List of period returns", required=True),
                MCPToolParam(name="confidence", type="number", description="Confidence level (default 0.95)", required=False),
            ],
            requires_sandbox=True,
            risk_level="medium",
        )
    )
    registry.register_tool(
        MCPToolSchema(
            name="dcf_valuation",
            description="Perform a discounted cash flow (DCF) valuation.",
            server_id="demo_financial_calc",
            parameters=[
                MCPToolParam(name="cash_flows", type="array", description="Projected annual cash flows", required=True),
                MCPToolParam(name="discount_rate", type="number", description="Discount rate (e.g. 0.10 for 10%)", required=True),
                MCPToolParam(name="terminal_growth", type="number", description="Terminal growth rate (e.g. 0.03 for 3%)", required=True),
            ],
            requires_sandbox=True,
            risk_level="low",
        )
    )

    logger.info(
        "Registry bootstrap complete: %d tools registered across %d servers",
        len(registry.all_tools()),
        3,
    )
