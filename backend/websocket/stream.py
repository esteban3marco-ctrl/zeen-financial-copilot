"""Stream LangGraph events over a WebSocket connection."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import WebSocket

from backend.websocket.protocol import (
    WSGateEvent,
    WSToken,
    WSToolResult,
    WSToolStart,
)

logger = logging.getLogger(__name__)

_GATE_KEYWORDS = {"pre_llm_gate", "post_llm_gate", "pre_tool_gate", "post_tool_gate"}


def _gate_name_from_event_name(name: str) -> str:
    """Map node name to gate identifier string."""
    for keyword in _GATE_KEYWORDS:
        if keyword in name:
            return keyword.replace("_gate", "")
    return name


async def _run_early_post_llm_gate(
    llm_buffer: list[str],
    websocket: WebSocket,
    request_id: str,
    risk_context_dict: dict[str, Any] | None,
    original_input: str,
    emitted_flag: list[bool],
) -> None:
    """
    Run post_llm gate evaluation after a brief delay (parallel to LLM streaming).
    Emits WSGateEvent for post_llm as soon as evaluation finishes (~350ms total).
    """
    # Wait briefly to collect initial LLM tokens before evaluating
    await asyncio.sleep(0.35)

    if emitted_flag[0]:
        return  # Already emitted by on_chain_end (shouldn't happen, but guard)

    partial_content = "".join(llm_buffer)
    action = "allow"
    reason = "Post-LLM gate passed (streaming evaluation)"
    metadata: dict[str, Any] = {"streaming": True}

    try:
        from risk_gates.gates.post_llm import run_post_llm_gate
        from risk_gates.schemas import PostLLMRequest, RiskContext, UserRole

        # Build RiskContext from state dict, with safe defaults
        rc_dict = risk_context_dict or {}
        user_role_raw = rc_dict.get("user_role", "basic")
        try:
            user_role = UserRole(user_role_raw)
        except (ValueError, KeyError):
            user_role = UserRole.BASIC

        risk_ctx = RiskContext(
            request_id=rc_dict.get("request_id", request_id),
            session_id=rc_dict.get("session_id", "stream"),
            user_id=rc_dict.get("user_id", "demo"),
            user_role=user_role,
        )

        req = PostLLMRequest(
            llm_response=partial_content or "(generating…)",
            risk_context=risk_ctx,
            original_input=original_input,
        )
        decision = await run_post_llm_gate(req)
        gate_dec = decision.gate_decision
        action = gate_dec.action.value if hasattr(gate_dec.action, "value") else str(gate_dec.action)
        reason = gate_dec.reason
        audit = gate_dec.audit
        metadata = {**(audit.metadata if audit else {}), "streaming": True}

    except Exception as exc:
        logger.debug("Early post_llm gate evaluation error (using allow): %s", exc)

    if emitted_flag[0]:
        return  # Re-check after the awaits above

    emitted_flag[0] = True
    ws_msg = WSGateEvent(gate="post_llm", action=action, reason=reason, metadata=metadata)
    try:
        await websocket.send_text(ws_msg.model_dump_json())
        logger.debug("Early post_llm gate emitted: action=%s latency=~350ms", action)
    except Exception as exc:
        logger.debug("Failed to send early post_llm gate event: %s", exc)


async def stream_graph_to_websocket(
    graph: Any,
    state_dict: dict[str, Any],
    config: dict[str, Any],
    websocket: WebSocket,
    request_id: str,
    risk_context_dict: dict[str, Any] | None = None,
    original_input: str = "",
) -> dict[str, Any]:
    """
    Stream LangGraph astream_events to the WebSocket.

    Returns the final accumulated state dict from the last __end__ event.
    Emits the post_llm gate in parallel with LLM streaming (~350ms after first token)
    rather than waiting for the full LLM response (~99s).
    """
    final_state: dict[str, Any] = {}
    start_ms = time.monotonic() * 1000

    # State for parallel post_llm gate evaluation
    llm_buffer: list[str] = []
    post_llm_emitted: list[bool] = [False]
    early_gate_task: asyncio.Task[None] | None = None

    try:
        async for event in graph.astream_events(state_dict, config=config, version="v2"):
            event_name: str = event.get("name", "")
            event_type: str = event.get("event", "")
            data: dict[str, Any] = event.get("data", {})
            logger.debug("STREAM_EVENT type=%s name=%s", event_type, event_name)

            # ── Gate events ────────────────────────────────────────────
            # Only process on_chain_END (has real evaluation result).
            # on_chain_START fires before the gate runs, has no output.
            if event_type == "on_chain_end" and any(
                kw in event_name for kw in _GATE_KEYWORDS
            ):
                gate_name = _gate_name_from_event_name(event_name)

                # Skip post_llm on_chain_end if already emitted early
                if gate_name == "post_llm" and post_llm_emitted[0]:
                    # Still capture final state output if available
                    output = data.get("output") or {}
                    if isinstance(output, dict) and output.get("gate_decisions"):
                        pass  # captured via __end__ event below
                    continue

                output = data.get("output") or {}
                gate_decision = None
                if isinstance(output, dict):
                    gate_decisions = output.get("gate_decisions", {})
                    gate_decision = gate_decisions.get(gate_name)

                action = "allow"
                reason = ""
                metadata: dict[str, Any] = {}

                if gate_decision and isinstance(gate_decision, dict):
                    action = gate_decision.get("action", "allow")
                    reason = gate_decision.get("reason", "")
                    audit = gate_decision.get("audit", {})
                    metadata = audit.get("metadata", {}) if isinstance(audit, dict) else {}
                elif hasattr(gate_decision, "action"):
                    action = gate_decision.action.value if hasattr(gate_decision.action, "value") else str(gate_decision.action)
                    reason = gate_decision.reason
                    metadata = gate_decision.audit.metadata if gate_decision.audit else {}

                # Mark as emitted before sending to avoid races
                if gate_name == "post_llm":
                    post_llm_emitted[0] = True

                ws_msg = WSGateEvent(
                    gate=gate_name,
                    action=action,
                    reason=reason,
                    metadata=metadata,
                )
                await websocket.send_text(ws_msg.model_dump_json())

            # ── LLM token streaming ────────────────────────────────────
            elif event_type == "on_chat_model_stream":
                chunk = data.get("chunk")
                content = ""
                if chunk is not None:
                    if hasattr(chunk, "content"):
                        raw = chunk.content
                        if isinstance(raw, str):
                            content = raw
                        elif isinstance(raw, list):
                            for part in raw:
                                if isinstance(part, dict) and part.get("type") == "text":
                                    content += part.get("text", "")
                                elif isinstance(part, str):
                                    content += part
                    elif isinstance(chunk, str):
                        content = chunk

                if content:
                    # Accumulate in buffer for early gate evaluation
                    llm_buffer.append(content)

                    # Launch early post_llm gate on first token (parallel task)
                    if early_gate_task is None and not post_llm_emitted[0]:
                        early_gate_task = asyncio.create_task(
                            _run_early_post_llm_gate(
                                llm_buffer,
                                websocket,
                                request_id,
                                risk_context_dict,
                                original_input,
                                post_llm_emitted,
                            )
                        )

                    ws_token = WSToken(content=content, request_id=request_id)
                    await websocket.send_text(ws_token.model_dump_json())

            # ── Tool start ─────────────────────────────────────────────
            elif event_type == "on_tool_start":
                tool_name = event_name or data.get("name", "unknown")
                call_id = data.get("id") or data.get("call_id") or ""
                params_preview: dict[str, Any] = data.get("input") or {}
                ws_tool_start = WSToolStart(
                    tool_name=tool_name,
                    call_id=call_id,
                    params_preview=params_preview if isinstance(params_preview, dict) else {},
                )
                await websocket.send_text(ws_tool_start.model_dump_json())

            # ── Tool result ────────────────────────────────────────────
            elif event_type == "on_tool_end":
                tool_name = event_name or data.get("name", "unknown")
                call_id = data.get("id") or data.get("call_id") or ""
                output = data.get("output")
                result_preview: str | None = None
                if output is not None:
                    preview = str(output)
                    result_preview = preview[:500] if len(preview) > 500 else preview

                ws_tool_result = WSToolResult(
                    tool_name=tool_name,
                    call_id=call_id,
                    status="success",
                    result_preview=result_preview,
                    execution_time_ms=0.0,
                )
                await websocket.send_text(ws_tool_result.model_dump_json())

            # ── Capture final state ────────────────────────────────────
            elif event_type == "on_chain_end" and event_name == "__end__":
                output = data.get("output", {})
                if isinstance(output, dict):
                    final_state = output

    except Exception as exc:
        logger.exception(
            "Error streaming graph events for request_id=%s: %s", request_id, exc
        )
        raise
    finally:
        # Cancel early gate task if still pending (e.g. graph failed)
        if early_gate_task is not None and not early_gate_task.done():
            early_gate_task.cancel()

    elapsed = time.monotonic() * 1000 - start_ms
    logger.info(
        "stream_graph_to_websocket complete: request_id=%s elapsed_ms=%.1f",
        request_id,
        elapsed,
    )
    return final_state
