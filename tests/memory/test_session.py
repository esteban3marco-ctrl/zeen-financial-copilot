"""Tests for SessionMemoryManager."""
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent_runtime.state import ToolResult
from memory.session import SessionMemoryManager


class TestSessionMemoryManager:
    def test_initial_state_empty(self) -> None:
        mgr = SessionMemoryManager()
        assert mgr.memory.context_window_messages == []
        assert mgr.memory.turn_count == 0

    def test_add_message(self) -> None:
        mgr = SessionMemoryManager()
        mgr.add_message(HumanMessage(content="hello"))
        assert len(mgr.memory.context_window_messages) == 1

    def test_context_window_trimmed(self) -> None:
        mgr = SessionMemoryManager(max_context_messages=3)
        for i in range(5):
            mgr.add_message(HumanMessage(content=f"msg {i}"))
        assert len(mgr.memory.context_window_messages) == 3
        # Last 3 messages are kept
        assert "msg 4" in str(mgr.memory.context_window_messages[-1].content)

    def test_add_tool_result(self) -> None:
        mgr = SessionMemoryManager()
        result = ToolResult(call_id="c1", tool_name="t1", status="success")
        mgr.add_tool_result(result)
        assert len(mgr.memory.recent_tool_results) == 1

    def test_tool_results_capped_at_10(self) -> None:
        mgr = SessionMemoryManager()
        for i in range(15):
            mgr.add_tool_result(ToolResult(call_id=f"c{i}", tool_name="t", status="success"))
        assert len(mgr.memory.recent_tool_results) == 10

    def test_detect_preferences_from_message(self) -> None:
        mgr = SessionMemoryManager()
        prefs = mgr.detect_preferences("I want to know about crypto and stock trading")
        pref_values = [p.value for p in prefs]
        assert "crypto" in pref_values
        assert "equities" in pref_values

    def test_no_preferences_detected_for_generic_text(self) -> None:
        mgr = SessionMemoryManager()
        prefs = mgr.detect_preferences("Hello, how are you?")
        assert prefs == []

    def test_preferences_not_duplicated(self) -> None:
        mgr = SessionMemoryManager()
        mgr.detect_preferences("I like stocks")
        mgr.detect_preferences("I like stocks again")
        equities_prefs = [p for p in mgr.memory.detected_preferences if p.value == "equities"]
        assert len(equities_prefs) == 1

    def test_increment_turn(self) -> None:
        mgr = SessionMemoryManager()
        mgr.increment_turn()
        mgr.increment_turn()
        assert mgr.memory.turn_count == 2

    def test_get_context_for_llm(self) -> None:
        mgr = SessionMemoryManager()
        msgs = [HumanMessage(content="q"), AIMessage(content="a")]
        for m in msgs:
            mgr.add_message(m)
        context = mgr.get_context_for_llm()
        assert len(context) == 2
