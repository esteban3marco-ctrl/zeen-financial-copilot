#!/usr/bin/env python
"""
Demo portfolio MCP server.

Runs as a JSON-RPC 2.0 stdio server that exposes:
  - get_portfolio(user_id)
  - get_holdings(user_id, symbol?)
"""
from __future__ import annotations

import json
import sys
from datetime import date
from typing import Any

# ── Mock data ────────────────────────────────────────────────────────────────

_HOLDINGS: list[dict[str, Any]] = [
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "shares": 50,
        "avg_cost": 155.20,
        "current_price": 189.30,
        "market_value": 9465.00,
        "gain_loss": 1705.00,
        "gain_loss_pct": 21.94,
        "asset_class": "equity",
        "sector": "Technology",
    },
    {
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "shares": 20,
        "avg_cost": 2750.00,
        "current_price": 3120.50,
        "market_value": 62410.00,
        "gain_loss": 7410.00,
        "gain_loss_pct": 13.47,
        "asset_class": "equity",
        "sector": "Communication Services",
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "shares": 35,
        "avg_cost": 280.40,
        "current_price": 415.60,
        "market_value": 14546.00,
        "gain_loss": 4732.00,
        "gain_loss_pct": 48.22,
        "asset_class": "equity",
        "sector": "Technology",
    },
    {
        "symbol": "BND",
        "name": "Vanguard Total Bond Market ETF",
        "shares": 200,
        "avg_cost": 76.50,
        "current_price": 73.80,
        "market_value": 14760.00,
        "gain_loss": -540.00,
        "gain_loss_pct": -3.53,
        "asset_class": "fixed_income",
        "sector": "Bonds",
    },
]


def _portfolio_summary(user_id: str) -> dict[str, Any]:
    total_value = sum(h["market_value"] for h in _HOLDINGS)
    total_cost = sum(h["avg_cost"] * h["shares"] for h in _HOLDINGS)
    total_gain = total_value - total_cost

    return {
        "user_id": user_id,
        "as_of": str(date.today()),
        "total_market_value": round(total_value, 2),
        "total_cost_basis": round(total_cost, 2),
        "total_gain_loss": round(total_gain, 2),
        "total_gain_loss_pct": round((total_gain / total_cost) * 100, 2),
        "num_positions": len(_HOLDINGS),
        "asset_allocation": {
            "equity": round(
                sum(h["market_value"] for h in _HOLDINGS if h["asset_class"] == "equity")
                / total_value * 100,
                1,
            ),
            "fixed_income": round(
                sum(h["market_value"] for h in _HOLDINGS if h["asset_class"] == "fixed_income")
                / total_value * 100,
                1,
            ),
        },
        "ytd_return_pct": 14.73,
        "one_year_return_pct": 22.15,
        "beta": 1.12,
        "dividend_yield_pct": 0.87,
    }


def _get_holdings(user_id: str, symbol: str | None = None) -> list[dict[str, Any]]:
    if symbol:
        return [h for h in _HOLDINGS if h["symbol"].upper() == symbol.upper()]
    return list(_HOLDINGS)


# ── JSON-RPC server ──────────────────────────────────────────────────────────

_TOOLS: dict[str, Any] = {
    "get_portfolio": {
        "description": "Retrieve the user's current portfolio summary.",
        "inputSchema": {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"],
        },
    },
    "get_holdings": {
        "description": "List individual holdings, optionally filtered by symbol.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "symbol": {"type": "string"},
            },
            "required": ["user_id"],
        },
    },
}


def _handle_request(req: dict[str, Any]) -> dict[str, Any]:
    rpc_id = req.get("id")
    method = req.get("method", "")
    params = req.get("params", {})

    def ok(result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": rpc_id, "result": result}

    def err(code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}

    if method == "initialize":
        return ok({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "demo_portfolio", "version": "1.0.0"},
        })

    if method == "tools/list":
        return ok({
            "tools": [
                {"name": name, **schema}
                for name, schema in _TOOLS.items()
            ]
        })

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "get_portfolio":
            user_id = arguments.get("user_id", "demo")
            result = _portfolio_summary(user_id)
            return ok({"content": [{"type": "text", "text": json.dumps(result)}]})

        if tool_name == "get_holdings":
            user_id = arguments.get("user_id", "demo")
            symbol = arguments.get("symbol")
            holdings_result = _get_holdings(user_id, symbol)
            return ok({"content": [{"type": "text", "text": json.dumps(holdings_result)}]})

        return err(-32601, f"Unknown tool: {tool_name}")

    return err(-32601, f"Method not found: {method}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = _handle_request(req)
        except Exception as exc:
            resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
        print(json.dumps(resp), flush=True)


if __name__ == "__main__":
    main()
