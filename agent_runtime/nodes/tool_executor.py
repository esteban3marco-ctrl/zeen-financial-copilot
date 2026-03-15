"""tool_executor node: dispatch to MCP or E2B sandbox, collect results."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Literal

from langchain_core.messages import ToolMessage

from agent_runtime.state import AgentError, AgentState, ErrorSeverity, ToolResult
from agent_runtime.tracing import Attrs, agent_span
from risk_gates.schemas import ToolCall

logger = logging.getLogger(__name__)

SANDBOX_REQUIRED_TOOLS: frozenset[str] = frozenset({
    "code_execute", "python_eval", "shell_exec",
    "file_write", "npm_install", "pip_install",
})

DEFAULT_TOOL_TIMEOUT_MS = 30_000


async def _execute_mcp_tool(tool_call: ToolCall) -> ToolResult:
    """Dispatch a tool call to the appropriate MCP server."""
    from tools.registry import get_registry  # lazy import to avoid circular deps

    start = time.monotonic() * 1000
    try:
        registry = await get_registry()
        result = await registry.call_tool(
            tool_name=tool_call.tool_name,
            params=tool_call.tool_params,
            call_id=tool_call.call_id,
        )
        return ToolResult(
            call_id=tool_call.call_id,
            tool_name=tool_call.tool_name,
            status="success",
            result=result,
            execution_time_ms=time.monotonic() * 1000 - start,
        )
    except asyncio.TimeoutError:
        return ToolResult(
            call_id=tool_call.call_id,
            tool_name=tool_call.tool_name,
            status="timeout",
            error_message=f"Tool '{tool_call.tool_name}' timed out",
            execution_time_ms=time.monotonic() * 1000 - start,
        )
    except Exception as exc:
        logger.exception("MCP tool '%s' failed", tool_call.tool_name)
        return ToolResult(
            call_id=tool_call.call_id,
            tool_name=tool_call.tool_name,
            status="error",
            error_message=str(exc),
            execution_time_ms=time.monotonic() * 1000 - start,
        )


async def _execute_sandbox_tool(tool_call: ToolCall, user_role: str) -> ToolResult:
    """Execute code in an E2B sandbox."""
    from tools.sandbox import run_in_sandbox  # lazy import

    start = time.monotonic() * 1000
    try:
        sandbox_result = await run_in_sandbox(
            call_id=tool_call.call_id,
            tool_name=tool_call.tool_name,
            code=tool_call.tool_params.get("code", ""),
            language=tool_call.tool_params.get("language", "python"),
            user_role=user_role,
        )
        sandbox_status: Literal["success", "error"] = "success" if sandbox_result.exit_code == 0 else "error"
        return ToolResult(
            call_id=tool_call.call_id,
            tool_name=tool_call.tool_name,
            status=sandbox_status,
            result={"stdout": sandbox_result.stdout, "stderr": sandbox_result.stderr},
            error_message=sandbox_result.stderr if sandbox_status == "error" else None,
            execution_time_ms=time.monotonic() * 1000 - start,
            sandbox_used=True,
        )
    except Exception as exc:
        logger.exception("Sandbox execution failed for tool '%s'", tool_call.tool_name)
        return ToolResult(
            call_id=tool_call.call_id,
            tool_name=tool_call.tool_name,
            status="error",
            error_message=str(exc),
            execution_time_ms=time.monotonic() * 1000 - start,
            sandbox_used=True,
        )


async def tool_executor(state: AgentState) -> dict[str, Any]:
    """Execute all authorized tool calls, collect results."""
    with agent_span(
        "node.tool_executor",
        **{
            Attrs.NODE_NAME: "tool_executor",
            Attrs.TOOL_ITERATION: state.iteration_count,
        },
    ) as span:
        if not state.current_tool_calls:
            return {"next_action": "respond"}

        user_role = state.risk_context.user_role if state.risk_context else "basic"
        results: list[ToolResult] = []
        tool_messages: list[ToolMessage] = []

        for tool_call in state.current_tool_calls:
            use_sandbox = tool_call.tool_name in SANDBOX_REQUIRED_TOOLS

            span.set_attribute(Attrs.TOOL_NAME, tool_call.tool_name)
            span.set_attribute(Attrs.TOOL_SANDBOX, use_sandbox)

            if use_sandbox:
                result = await _execute_sandbox_tool(tool_call, user_role)
            else:
                result = await _execute_mcp_tool(tool_call)

            results.append(result)
            span.set_attribute(Attrs.TOOL_STATUS, result.status)
            span.set_attribute(Attrs.TOOL_LATENCY_MS, result.execution_time_ms)

            # Build ToolMessage for the conversation
            content = (
                str(result.result)
                if result.result is not None
                else result.error_message or "No result"
            )
            tool_messages.append(
                ToolMessage(
                    content=content,
                    tool_call_id=tool_call.call_id,
                    name=tool_call.tool_name,
                )
            )

        logger.info(
            "tool_executor: executed %d tools iter=%d",
            len(results),
            state.iteration_count,
        )

        return {
            "messages": tool_messages,
            "tool_results": list(state.tool_results) + results,
            "iteration_count": state.iteration_count + 1,
            "next_action": "loop_back",
        }
