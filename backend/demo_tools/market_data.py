#!/usr/bin/env python
"""
Demo market data MCP server.

Runs as a JSON-RPC 2.0 stdio server that exposes:
  - get_quote(symbol)
  - get_market_summary()
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from typing import Any

# ── Mock data ────────────────────────────────────────────────────────────────

_QUOTES: dict[str, dict[str, Any]] = {
    "AAPL": {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "price": 189.30,
        "change": 2.15,
        "change_pct": 1.15,
        "volume": 58_324_100,
        "avg_volume": 55_000_000,
        "market_cap": 2_970_000_000_000,
        "pe_ratio": 30.2,
        "52w_high": 199.62,
        "52w_low": 124.17,
        "dividend_yield": 0.51,
        "beta": 1.28,
        "eps": 6.26,
    },
    "GOOGL": {
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "price": 3120.50,
        "change": 18.75,
        "change_pct": 0.60,
        "volume": 1_230_400,
        "avg_volume": 1_100_000,
        "market_cap": 1_970_000_000_000,
        "pe_ratio": 27.4,
        "52w_high": 3_200.00,
        "52w_low": 2_015.00,
        "dividend_yield": 0.0,
        "beta": 1.05,
        "eps": 113.88,
    },
    "MSFT": {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "price": 415.60,
        "change": -1.40,
        "change_pct": -0.34,
        "volume": 22_850_000,
        "avg_volume": 20_000_000,
        "market_cap": 3_090_000_000_000,
        "pe_ratio": 36.1,
        "52w_high": 430.82,
        "52w_low": 309.45,
        "dividend_yield": 0.72,
        "beta": 0.90,
        "eps": 11.51,
    },
    "BND": {
        "symbol": "BND",
        "name": "Vanguard Total Bond Market ETF",
        "price": 73.80,
        "change": 0.05,
        "change_pct": 0.07,
        "volume": 5_430_000,
        "avg_volume": 6_000_000,
        "market_cap": None,
        "pe_ratio": None,
        "52w_high": 78.50,
        "52w_low": 70.12,
        "dividend_yield": 3.95,
        "beta": 0.02,
        "eps": None,
    },
    "SPY": {
        "symbol": "SPY",
        "name": "SPDR S&P 500 ETF Trust",
        "price": 510.25,
        "change": 3.80,
        "change_pct": 0.75,
        "volume": 78_000_000,
        "avg_volume": 72_000_000,
        "market_cap": None,
        "pe_ratio": 22.8,
        "52w_high": 524.61,
        "52w_low": 410.00,
        "dividend_yield": 1.30,
        "beta": 1.00,
        "eps": None,
    },
}


def _get_quote(symbol: str) -> dict[str, Any]:
    sym = symbol.upper()
    if sym in _QUOTES:
        return {**_QUOTES[sym], "timestamp": datetime.utcnow().isoformat(), "as_of": str(date.today())}
    # Generic fallback
    return {
        "symbol": sym,
        "name": f"{sym} (Unknown)",
        "price": 100.00,
        "change": 0.0,
        "change_pct": 0.0,
        "volume": 0,
        "error": None,
        "timestamp": datetime.utcnow().isoformat(),
        "as_of": str(date.today()),
        "note": "Symbol not in demo dataset — returning placeholder values",
    }


def _get_market_summary() -> dict[str, Any]:
    return {
        "as_of": str(date.today()),
        "timestamp": datetime.utcnow().isoformat(),
        "indices": {
            "S&P 500": {"value": 5100.25, "change_pct": 0.75, "ytd_pct": 8.32},
            "NASDAQ Composite": {"value": 16_250.00, "change_pct": 0.92, "ytd_pct": 11.45},
            "Dow Jones": {"value": 38_750.00, "change_pct": 0.45, "ytd_pct": 5.12},
            "Russell 2000": {"value": 2050.30, "change_pct": -0.22, "ytd_pct": 2.88},
            "VIX": {"value": 14.52, "change_pct": -3.10, "ytd_pct": None},
        },
        "sector_performance": {
            "Technology": 1.15,
            "Healthcare": 0.32,
            "Financials": 0.58,
            "Energy": -0.45,
            "Consumer Discretionary": 0.72,
            "Industrials": 0.28,
            "Utilities": -0.18,
            "Real Estate": -0.62,
            "Materials": 0.14,
            "Communication Services": 0.89,
            "Consumer Staples": -0.05,
        },
        "economic_indicators": {
            "10y_treasury_yield_pct": 4.28,
            "fed_funds_rate_pct": 5.25,
            "cpi_yoy_pct": 3.1,
            "unemployment_rate_pct": 3.8,
            "gdp_growth_qoq_pct": 2.4,
        },
        "market_breadth": {
            "advancing": 312,
            "declining": 188,
            "unchanged": 10,
        },
        "sentiment": "neutral_to_bullish",
    }


# ── JSON-RPC server ──────────────────────────────────────────────────────────

_TOOLS: dict[str, Any] = {
    "get_quote": {
        "description": "Get the latest stock quote for a given ticker symbol.",
        "inputSchema": {
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "Ticker symbol (e.g. AAPL)"}},
            "required": ["symbol"],
        },
    },
    "get_market_summary": {
        "description": "Get a high-level summary of major market indices and sector performance.",
        "inputSchema": {
            "type": "object",
            "properties": {},
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
            "serverInfo": {"name": "demo_market_data", "version": "1.0.0"},
        })

    if method == "tools/list":
        return ok({
            "tools": [{"name": name, **schema} for name, schema in _TOOLS.items()]
        })

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "get_quote":
            symbol = arguments.get("symbol", "SPY")
            result = _get_quote(symbol)
            return ok({"content": [{"type": "text", "text": json.dumps(result)}]})

        if tool_name == "get_market_summary":
            result = _get_market_summary()
            return ok({"content": [{"type": "text", "text": json.dumps(result)}]})

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
