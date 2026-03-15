"""LangGraph StateGraph: wire all nodes and conditional edges."""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from agent_runtime.nodes.error_handler import error_handler
from agent_runtime.nodes.input_validator import input_validator
from agent_runtime.nodes.llm_invoke import llm_invoke
from agent_runtime.nodes.post_llm_gate import post_llm_gate
from agent_runtime.nodes.post_tool_gate import post_tool_gate
from agent_runtime.nodes.pre_llm_gate import pre_llm_gate
from agent_runtime.nodes.pre_tool_gate import pre_tool_gate
from agent_runtime.nodes.response_formatter import response_formatter
from agent_runtime.nodes.tool_executor import tool_executor
from agent_runtime.nodes.tool_router import tool_router
from agent_runtime.state import AgentState


def _route_after_validator(state: AgentState) -> str:
    return "error_handler" if state.next_action == "error" else "pre_llm_gate"


def _route_after_pre_llm(state: AgentState) -> str:
    return "error_handler" if state.next_action == "error" else "llm_invoke"


def _route_after_post_llm(state: AgentState) -> str:
    if state.next_action == "error":
        return "error_handler"
    return "tool_router"


def _route_after_tool_router(state: AgentState) -> str:
    if state.next_action == "route_tools":
        return "pre_tool_gate"
    return "response_formatter"


def _route_after_pre_tool(state: AgentState) -> str:
    if state.next_action == "error":
        return "error_handler"
    return "tool_executor"


def _route_after_post_tool(state: AgentState) -> str:
    # Always loop back to LLM after tool execution
    return "llm_invoke"


def _route_after_error(state: AgentState) -> Any:
    return END


def _route_after_formatter(state: AgentState) -> Any:
    return END


def build_graph(checkpointer: Any = None) -> Any:
    """Build and compile the Staq/Zeen agent StateGraph."""
    graph = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────────────
    graph.add_node("input_validator", input_validator)
    graph.add_node("pre_llm_gate", pre_llm_gate)
    graph.add_node("llm_invoke", llm_invoke)
    graph.add_node("post_llm_gate", post_llm_gate)
    graph.add_node("tool_router", tool_router)
    graph.add_node("pre_tool_gate", pre_tool_gate)
    graph.add_node("tool_executor", tool_executor)
    graph.add_node("post_tool_gate", post_tool_gate)
    graph.add_node("response_formatter", response_formatter)
    graph.add_node("error_handler", error_handler)

    # ── Entry point ────────────────────────────────────────────────
    graph.add_edge(START, "input_validator")

    # ── Conditional edges ──────────────────────────────────────────
    graph.add_conditional_edges(
        "input_validator",
        _route_after_validator,
        {"error_handler": "error_handler", "pre_llm_gate": "pre_llm_gate"},
    )
    graph.add_conditional_edges(
        "pre_llm_gate",
        _route_after_pre_llm,
        {"error_handler": "error_handler", "llm_invoke": "llm_invoke"},
    )
    graph.add_edge("llm_invoke", "post_llm_gate")
    graph.add_conditional_edges(
        "post_llm_gate",
        _route_after_post_llm,
        {"error_handler": "error_handler", "tool_router": "tool_router"},
    )
    graph.add_conditional_edges(
        "tool_router",
        _route_after_tool_router,
        {"pre_tool_gate": "pre_tool_gate", "response_formatter": "response_formatter"},
    )
    graph.add_conditional_edges(
        "pre_tool_gate",
        _route_after_pre_tool,
        {"error_handler": "error_handler", "tool_executor": "tool_executor"},
    )
    graph.add_edge("tool_executor", "post_tool_gate")
    graph.add_conditional_edges(
        "post_tool_gate",
        _route_after_post_tool,
        {"llm_invoke": "llm_invoke"},
    )
    graph.add_conditional_edges(
        "response_formatter",
        _route_after_formatter,
        {END: END},
    )
    graph.add_conditional_edges(
        "error_handler",
        _route_after_error,
        {END: END},
    )

    if checkpointer:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()
