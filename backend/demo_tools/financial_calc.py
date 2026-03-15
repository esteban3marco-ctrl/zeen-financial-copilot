"""
Financial calculation functions executed inside the E2B sandbox.

This module is NOT an MCP server. It provides pure Python functions
whose source the agent copies into a sandbox code string for execution.

Functions here are also importable directly for unit testing.
"""
from __future__ import annotations

import math
import statistics
from typing import cast


def sharpe_ratio(
    returns: list[float],
    risk_free_rate: float = 0.05,
) -> float:
    """
    Calculate the annualised Sharpe ratio for a list of periodic returns.

    Parameters
    ----------
    returns:
        List of period (e.g. monthly) returns as decimals (0.05 = 5%).
    risk_free_rate:
        Annual risk-free rate as a decimal (default 0.05 = 5%).

    Returns
    -------
    float
        Annualised Sharpe ratio. Returns 0.0 if standard deviation is zero.
    """
    if len(returns) < 2:
        return 0.0

    n = len(returns)
    # Convert annual risk-free rate to per-period rate (assuming monthly)
    periods_per_year = 12
    period_rf = (1 + risk_free_rate) ** (1 / periods_per_year) - 1

    excess = [r - period_rf for r in returns]
    mean_excess: float = cast(float, statistics.mean(excess))
    std_excess: float = cast(float, statistics.stdev(excess))

    if std_excess == 0.0:
        return 0.0

    # Annualise
    return float(round((mean_excess / std_excess) * math.sqrt(periods_per_year), 4))


def value_at_risk(
    returns: list[float],
    confidence: float = 0.95,
) -> float:
    """
    Calculate the historical Value at Risk (VaR) at the given confidence level.

    Parameters
    ----------
    returns:
        List of period returns as decimals.
    confidence:
        Confidence level (default 0.95 for 95% VaR).

    Returns
    -------
    float
        VaR as a positive number representing the potential loss at the
        (1 - confidence) percentile. E.g. 0.02 means 2% potential loss.
    """
    if not returns:
        return 0.0

    sorted_returns = sorted(returns)
    index = int((1 - confidence) * len(sorted_returns))
    index = max(0, min(index, len(sorted_returns) - 1))
    var = -sorted_returns[index]
    return round(var, 6)


def dcf_valuation(
    cash_flows: list[float],
    discount_rate: float,
    terminal_growth: float,
) -> float:
    """
    Discounted Cash Flow (DCF) valuation with Gordon Growth Model terminal value.

    Parameters
    ----------
    cash_flows:
        Projected annual free cash flows (e.g. [100, 110, 121, 133, 146]).
    discount_rate:
        Annual discount rate as a decimal (e.g. 0.10 for 10%).
    terminal_growth:
        Terminal (perpetuity) growth rate as a decimal (e.g. 0.03 for 3%).

    Returns
    -------
    float
        Estimated intrinsic value (sum of PV of cash flows + PV of terminal value).

    Raises
    ------
    ValueError
        If discount_rate <= terminal_growth (Gordon Growth Model constraint).
    """
    if not cash_flows:
        return 0.0

    if discount_rate <= terminal_growth:
        raise ValueError(
            f"discount_rate ({discount_rate}) must be greater than "
            f"terminal_growth ({terminal_growth}) for Gordon Growth Model"
        )

    pv_sum = 0.0
    for t, cf in enumerate(cash_flows, start=1):
        pv_sum += cf / (1 + discount_rate) ** t

    # Terminal value using last cash flow grown by terminal_growth for one more year
    last_cf = cash_flows[-1]
    terminal_cf = last_cf * (1 + terminal_growth)
    terminal_value = terminal_cf / (discount_rate - terminal_growth)
    n = len(cash_flows)
    pv_terminal = terminal_value / (1 + discount_rate) ** n

    return round(pv_sum + pv_terminal, 2)


# ── Sandbox code template ────────────────────────────────────────────────────

SANDBOX_PREAMBLE = '''
import math, statistics

def sharpe_ratio(returns, risk_free_rate=0.05):
    if len(returns) < 2:
        return 0.0
    periods_per_year = 12
    period_rf = (1 + risk_free_rate) ** (1 / periods_per_year) - 1
    excess = [r - period_rf for r in returns]
    mean_excess = statistics.mean(excess)
    std_excess = statistics.stdev(excess)
    if std_excess == 0.0:
        return 0.0
    return round((mean_excess / std_excess) * math.sqrt(periods_per_year), 4)

def value_at_risk(returns, confidence=0.95):
    if not returns:
        return 0.0
    sorted_returns = sorted(returns)
    index = int((1 - confidence) * len(sorted_returns))
    index = max(0, min(index, len(sorted_returns) - 1))
    return round(-sorted_returns[index], 6)

def dcf_valuation(cash_flows, discount_rate, terminal_growth):
    if not cash_flows:
        return 0.0
    if discount_rate <= terminal_growth:
        raise ValueError("discount_rate must exceed terminal_growth")
    pv_sum = sum(cf / (1 + discount_rate) ** t for t, cf in enumerate(cash_flows, 1))
    terminal_cf = cash_flows[-1] * (1 + terminal_growth)
    pv_terminal = (terminal_cf / (discount_rate - terminal_growth)) / (1 + discount_rate) ** len(cash_flows)
    return round(pv_sum + pv_terminal, 2)
'''
