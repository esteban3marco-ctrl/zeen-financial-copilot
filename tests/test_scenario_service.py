"""
Tests for backend/services/scenario_service.py.

Verifies that SCENARIOS dict is properly populated with expected data.
"""
from __future__ import annotations

import pytest

from backend.services.scenario_service import SCENARIOS, DemoScenario
from risk_gates.schemas import UserRole


def test_scenarios_loaded():
    """There must be exactly 3 predefined demo scenarios."""
    assert len(SCENARIOS) == 3


def test_all_scenario_ids_present():
    """All three expected scenario IDs must be keys in SCENARIOS."""
    expected = {"safe_portfolio", "moderate_trading", "high_risk_blocked"}
    assert set(SCENARIOS.keys()) == expected


def test_scenarios_are_demo_scenario_instances():
    """Every value in SCENARIOS must be a DemoScenario dataclass."""
    for s in SCENARIOS.values():
        assert isinstance(s, DemoScenario)


# ------------------------------------------------------------------
# safe_portfolio
# ------------------------------------------------------------------

def test_safe_portfolio_scenario_exists():
    assert "safe_portfolio" in SCENARIOS


def test_safe_portfolio_risk_level():
    s = SCENARIOS["safe_portfolio"]
    assert s.risk_level == "low"


def test_safe_portfolio_message_content():
    s = SCENARIOS["safe_portfolio"]
    # Message should reference portfolio or Sharpe ratio
    assert "portfolio" in s.message.lower() or "sharpe" in s.message.lower()


def test_safe_portfolio_role():
    s = SCENARIOS["safe_portfolio"]
    assert s.role == UserRole.BASIC


def test_safe_portfolio_scenario_id_matches_key():
    s = SCENARIOS["safe_portfolio"]
    assert s.scenario_id == "safe_portfolio"


def test_safe_portfolio_has_description():
    s = SCENARIOS["safe_portfolio"]
    assert len(s.description) > 0


# ------------------------------------------------------------------
# moderate_trading
# ------------------------------------------------------------------

def test_moderate_trading_scenario_exists():
    assert "moderate_trading" in SCENARIOS


def test_moderate_trading_risk_level():
    s = SCENARIOS["moderate_trading"]
    assert s.risk_level == "medium"


def test_moderate_trading_role():
    s = SCENARIOS["moderate_trading"]
    assert s.role == UserRole.BASIC


def test_moderate_trading_scenario_id_matches_key():
    s = SCENARIOS["moderate_trading"]
    assert s.scenario_id == "moderate_trading"


def test_moderate_trading_has_message():
    s = SCENARIOS["moderate_trading"]
    assert len(s.message) > 0


# ------------------------------------------------------------------
# high_risk_blocked
# ------------------------------------------------------------------

def test_high_risk_blocked_scenario_exists():
    assert "high_risk_blocked" in SCENARIOS


def test_high_risk_blocked_risk_level():
    s = SCENARIOS["high_risk_blocked"]
    assert s.risk_level == "high"


def test_high_risk_blocked_message_contains_injection():
    s = SCENARIOS["high_risk_blocked"]
    # This scenario is a prompt injection attempt
    msg_lower = s.message.lower()
    assert "ignore" in msg_lower or "instruction" in msg_lower


def test_high_risk_blocked_role():
    s = SCENARIOS["high_risk_blocked"]
    assert s.role == UserRole.BASIC


def test_high_risk_blocked_scenario_id_matches_key():
    s = SCENARIOS["high_risk_blocked"]
    assert s.scenario_id == "high_risk_blocked"


# ------------------------------------------------------------------
# Cross-scenario consistency checks
# ------------------------------------------------------------------

def test_all_scenarios_have_non_empty_message():
    for sid, s in SCENARIOS.items():
        assert len(s.message) > 0, f"Scenario {sid!r} has empty message"


def test_all_scenarios_have_non_empty_description():
    for sid, s in SCENARIOS.items():
        assert len(s.description) > 0, f"Scenario {sid!r} has empty description"


def test_risk_levels_are_valid():
    valid_levels = {"low", "medium", "high"}
    for sid, s in SCENARIOS.items():
        assert s.risk_level in valid_levels, f"Scenario {sid!r} has invalid risk_level"


def test_scenarios_are_frozen():
    """DemoScenario is a frozen dataclass — mutation must raise TypeError."""
    s = SCENARIOS["safe_portfolio"]
    with pytest.raises((TypeError, AttributeError)):
        s.risk_level = "extreme"  # type: ignore[misc]
