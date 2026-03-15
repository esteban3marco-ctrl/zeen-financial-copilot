"""Tests for graph construction and conditional edge routing."""
from __future__ import annotations

import pytest

from agent_runtime.graph import (
    _route_after_post_llm,
    _route_after_pre_llm,
    _route_after_tool_router,
    _route_after_validator,
    build_graph,
)
from agent_runtime.state import AgentError, AgentState, ErrorSeverity


def _state_with_action(action: str) -> AgentState:
    return AgentState(next_action=action)


class TestBuildGraph:
    def test_graph_compiles(self) -> None:
        graph = build_graph()
        assert graph is not None

    def test_graph_has_nodes(self) -> None:
        graph = build_graph()
        # LangGraph compiled graph has a get_graph method
        g = graph.get_graph()
        node_names = set(g.nodes.keys())
        expected = {
            "input_validator", "pre_llm_gate", "llm_invoke",
            "post_llm_gate", "tool_router", "pre_tool_gate",
            "tool_executor", "post_tool_gate", "response_formatter",
            "error_handler", "__start__", "__end__",
        }
        assert expected.issubset(node_names)


class TestConditionalEdges:
    def test_validator_routes_to_error_on_error(self) -> None:
        state = _state_with_action("error")
        assert _route_after_validator(state) == "error_handler"

    def test_validator_routes_to_pre_llm_gate(self) -> None:
        state = _state_with_action("continue")
        assert _route_after_validator(state) == "pre_llm_gate"

    def test_pre_llm_gate_routes_to_error(self) -> None:
        state = _state_with_action("error")
        assert _route_after_pre_llm(state) == "error_handler"

    def test_pre_llm_gate_routes_to_llm(self) -> None:
        state = _state_with_action("continue")
        assert _route_after_pre_llm(state) == "llm_invoke"

    def test_post_llm_routes_to_error(self) -> None:
        state = _state_with_action("error")
        assert _route_after_post_llm(state) == "error_handler"

    def test_post_llm_routes_to_tool_router(self) -> None:
        state = _state_with_action("route_tools")
        assert _route_after_post_llm(state) == "tool_router"

    def test_post_llm_routes_to_tool_router_on_respond(self) -> None:
        state = _state_with_action("respond")
        # post_llm always goes to tool_router to decide
        assert _route_after_post_llm(state) == "tool_router"

    def test_tool_router_routes_to_pre_tool(self) -> None:
        state = _state_with_action("route_tools")
        assert _route_after_tool_router(state) == "pre_tool_gate"

    def test_tool_router_routes_to_response_formatter(self) -> None:
        state = _state_with_action("respond")
        assert _route_after_tool_router(state) == "response_formatter"
