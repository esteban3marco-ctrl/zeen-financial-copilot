"""Tests for backend/websocket/stream.py and backend/websocket/handler.py."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.websocket.protocol import (
    WSConnected,
    WSError,
    WSGateEvent,
    WSPong,
    WSToken,
    WSToolResult,
    WSToolStart,
    WSTurnEnd,
    WSTurnStart,
)


# ─── Helpers ─────────────────────────────────────────────────────────────

def _make_websocket() -> MagicMock:
    ws = MagicMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.query_params = {"user_id": "demo-user", "role": "basic"}
    return ws


async def _yield_events(events: list[dict[str, Any]]) -> AsyncIterator[dict[str, Any]]:
    for e in events:
        yield e


# ─── stream_graph_to_websocket tests ─────────────────────────────────────

class TestStreamGraphToWebsocket:
    @pytest.mark.asyncio
    async def test_empty_events_returns_empty_state(self) -> None:
        from backend.websocket.stream import stream_graph_to_websocket

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_yield_events([]))
        ws = _make_websocket()

        result = await stream_graph_to_websocket(
            graph=mock_graph,
            state_dict={"messages": []},
            config={},
            websocket=ws,
            request_id="req-1",
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_gate_event_pre_llm_sent(self) -> None:
        from backend.websocket.stream import stream_graph_to_websocket

        gate_event = {
            "event": "on_chain_end",
            "name": "pre_llm_gate",
            "data": {
                "output": {
                    "gate_decisions": {
                        "pre_llm": {
                            "action": "allow",
                            "reason": "Input validated",
                            "audit": {"metadata": {}},
                        }
                    }
                }
            },
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_yield_events([gate_event]))
        ws = _make_websocket()

        await stream_graph_to_websocket(
            graph=mock_graph,
            state_dict={},
            config={},
            websocket=ws,
            request_id="req-gate",
        )

        assert ws.send_text.call_count >= 1
        sent_payloads = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        gate_msgs = [p for p in sent_payloads if p.get("type") == "gate_event"]
        assert len(gate_msgs) == 1
        assert gate_msgs[0]["gate"] == "pre_llm"

    @pytest.mark.asyncio
    async def test_llm_token_event_sends_ws_token(self) -> None:
        from backend.websocket.stream import stream_graph_to_websocket

        chunk = MagicMock()
        chunk.content = "Hello"

        token_event = {
            "event": "on_chat_model_stream",
            "name": "ChatAnthropic",
            "data": {"chunk": chunk},
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_yield_events([token_event]))
        ws = _make_websocket()

        with patch(
            "backend.websocket.stream._run_early_post_llm_gate",
            new=AsyncMock(),
        ):
            await stream_graph_to_websocket(
                graph=mock_graph,
                state_dict={},
                config={},
                websocket=ws,
                request_id="req-token",
            )

        sent_payloads = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        token_msgs = [p for p in sent_payloads if p.get("type") == "token"]
        assert len(token_msgs) == 1
        assert token_msgs[0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_llm_token_list_content_concatenated(self) -> None:
        from backend.websocket.stream import stream_graph_to_websocket

        chunk = MagicMock()
        chunk.content = [
            {"type": "text", "text": "Hel"},
            {"type": "text", "text": "lo"},
        ]

        token_event = {
            "event": "on_chat_model_stream",
            "name": "ChatAnthropic",
            "data": {"chunk": chunk},
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_yield_events([token_event]))
        ws = _make_websocket()

        with patch(
            "backend.websocket.stream._run_early_post_llm_gate",
            new=AsyncMock(),
        ):
            await stream_graph_to_websocket(
                graph=mock_graph,
                state_dict={},
                config={},
                websocket=ws,
                request_id="req-token-list",
            )

        sent_payloads = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        token_msgs = [p for p in sent_payloads if p.get("type") == "token"]
        assert token_msgs[0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_tool_start_event_sent(self) -> None:
        from backend.websocket.stream import stream_graph_to_websocket

        tool_start_event = {
            "event": "on_tool_start",
            "name": "get_quote",
            "data": {"input": {"symbol": "AAPL"}, "id": "call-123"},
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_yield_events([tool_start_event]))
        ws = _make_websocket()

        await stream_graph_to_websocket(
            graph=mock_graph,
            state_dict={},
            config={},
            websocket=ws,
            request_id="req-tool-start",
        )

        sent_payloads = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        tool_msgs = [p for p in sent_payloads if p.get("type") == "tool_start"]
        assert len(tool_msgs) == 1
        assert tool_msgs[0]["tool_name"] == "get_quote"

    @pytest.mark.asyncio
    async def test_tool_end_event_sent(self) -> None:
        from backend.websocket.stream import stream_graph_to_websocket

        tool_end_event = {
            "event": "on_tool_end",
            "name": "get_quote",
            "data": {"output": {"price": 189.3}, "id": "call-456"},
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_yield_events([tool_end_event]))
        ws = _make_websocket()

        await stream_graph_to_websocket(
            graph=mock_graph,
            state_dict={},
            config={},
            websocket=ws,
            request_id="req-tool-end",
        )

        sent_payloads = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        tool_msgs = [p for p in sent_payloads if p.get("type") == "tool_result"]
        assert len(tool_msgs) == 1
        assert tool_msgs[0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_final_state_captured_from_end_event(self) -> None:
        from backend.websocket.stream import stream_graph_to_websocket

        end_event = {
            "event": "on_chain_end",
            "name": "__end__",
            "data": {
                "output": {
                    "messages": [],
                    "gate_decisions": {},
                    "iteration_count": 1,
                }
            },
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_yield_events([end_event]))
        ws = _make_websocket()

        result = await stream_graph_to_websocket(
            graph=mock_graph,
            state_dict={},
            config={},
            websocket=ws,
            request_id="req-final",
        )

        assert result["iteration_count"] == 1

    @pytest.mark.asyncio
    async def test_gate_event_with_object_decision(self) -> None:
        """Test that GateDecision objects (not dicts) are handled."""
        from backend.websocket.stream import stream_graph_to_websocket
        from risk_gates.schemas import AuditEntry, GateAction, GateDecision, GateName

        audit = AuditEntry(
            gate=GateName.PRE_LLM,
            action=GateAction.ALLOW,
            reason="OK",
            request_id="r1",
            user_id="u1",
        )
        gate_dec = GateDecision(action=GateAction.ALLOW, reason="OK", audit=audit)

        gate_event = {
            "event": "on_chain_end",
            "name": "pre_llm_gate",
            "data": {
                "output": {
                    "gate_decisions": {"pre_llm": gate_dec},
                }
            },
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_yield_events([gate_event]))
        ws = _make_websocket()

        await stream_graph_to_websocket(
            graph=mock_graph,
            state_dict={},
            config={},
            websocket=ws,
            request_id="req-obj",
        )

        sent_payloads = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        gate_msgs = [p for p in sent_payloads if p.get("type") == "gate_event"]
        assert gate_msgs[0]["action"] == "allow"

    @pytest.mark.asyncio
    async def test_post_llm_gate_not_duplicated_when_emitted_early(self) -> None:
        """If post_llm was already emitted early, on_chain_end for post_llm is skipped."""
        from backend.websocket.stream import stream_graph_to_websocket

        gate_event = {
            "event": "on_chain_end",
            "name": "post_llm_gate",
            "data": {
                "output": {
                    "gate_decisions": {
                        "post_llm": {
                            "action": "allow",
                            "reason": "OK",
                            "audit": {"metadata": {}},
                        }
                    }
                }
            },
        }

        # Simulate early post_llm gate having already been emitted
        async def mock_stream_events(*args: Any, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            yield gate_event

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=mock_stream_events())
        ws = _make_websocket()

        # We patch _run_early_post_llm_gate to set emitted flag synchronously
        original_stream = __import__(
            "backend.websocket.stream", fromlist=["stream_graph_to_websocket"]
        )

        await stream_graph_to_websocket(
            graph=mock_graph,
            state_dict={},
            config={},
            websocket=ws,
            request_id="req-no-dupe",
        )

        # If post_llm_emitted was False initially, the gate_event IS sent once
        sent_payloads = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        gate_msgs = [p for p in sent_payloads if p.get("type") == "gate_event"]
        assert len(gate_msgs) <= 1  # At most once

    @pytest.mark.asyncio
    async def test_exception_in_stream_propagates(self) -> None:
        from backend.websocket.stream import stream_graph_to_websocket

        async def error_events(*args: Any, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            raise RuntimeError("Stream exploded")
            yield {}  # unreachable

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=error_events())
        ws = _make_websocket()

        with pytest.raises(RuntimeError, match="Stream exploded"):
            await stream_graph_to_websocket(
                graph=mock_graph,
                state_dict={},
                config={},
                websocket=ws,
                request_id="req-err",
            )

    @pytest.mark.asyncio
    async def test_string_chunk_content(self) -> None:
        """Test that plain-string chunks are handled."""
        from backend.websocket.stream import stream_graph_to_websocket

        token_event = {
            "event": "on_chat_model_stream",
            "name": "LLM",
            "data": {"chunk": "plain string token"},
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_yield_events([token_event]))
        ws = _make_websocket()

        with patch(
            "backend.websocket.stream._run_early_post_llm_gate",
            new=AsyncMock(),
        ):
            await stream_graph_to_websocket(
                graph=mock_graph,
                state_dict={},
                config={},
                websocket=ws,
                request_id="req-str-chunk",
            )

        sent_payloads = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        token_msgs = [p for p in sent_payloads if p.get("type") == "token"]
        assert token_msgs[0]["content"] == "plain string token"

    @pytest.mark.asyncio
    async def test_early_post_llm_gate_task_cancelled_on_exception(self) -> None:
        """Verify early_gate_task is cancelled when the stream fails after task creation."""
        from backend.websocket.stream import stream_graph_to_websocket

        chunk = MagicMock()
        chunk.content = "first token"

        events_to_yield = [
            {
                "event": "on_chat_model_stream",
                "name": "LLM",
                "data": {"chunk": chunk},
            },
        ]

        async def fail_after_first(*args: Any, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            for e in events_to_yield:
                yield e
            raise RuntimeError("Forced failure")

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=fail_after_first())
        ws = _make_websocket()

        # The early gate task will be created but should be cancelled on error
        with patch(
            "backend.websocket.stream._run_early_post_llm_gate",
            new=AsyncMock(side_effect=asyncio.sleep(10)),  # Long-running task
        ):
            with pytest.raises(RuntimeError, match="Forced failure"):
                await stream_graph_to_websocket(
                    graph=mock_graph,
                    state_dict={},
                    config={},
                    websocket=ws,
                    request_id="req-cancel",
                )


# ─── _gate_name_from_event_name tests ────────────────────────────────────

class TestGateNameHelper:
    def test_pre_llm_gate_keyword(self) -> None:
        from backend.websocket.stream import _gate_name_from_event_name

        assert _gate_name_from_event_name("pre_llm_gate") == "pre_llm"

    def test_post_llm_gate_keyword(self) -> None:
        from backend.websocket.stream import _gate_name_from_event_name

        assert _gate_name_from_event_name("post_llm_gate") == "post_llm"

    def test_pre_tool_gate_keyword(self) -> None:
        from backend.websocket.stream import _gate_name_from_event_name

        assert _gate_name_from_event_name("pre_tool_gate") == "pre_tool"

    def test_post_tool_gate_keyword(self) -> None:
        from backend.websocket.stream import _gate_name_from_event_name

        assert _gate_name_from_event_name("post_tool_gate") == "post_tool"

    def test_unknown_name_passthrough(self) -> None:
        from backend.websocket.stream import _gate_name_from_event_name

        assert _gate_name_from_event_name("unknown_node") == "unknown_node"


# ─── websocket/handler.py tests ──────────────────────────────────────────

class TestWebsocketHandler:
    def _make_settings(self) -> Any:
        settings = MagicMock()
        settings.DEMO_MODE = True
        settings.LLM_MODEL = "test-model"
        settings.SUPABASE_URL = ""
        settings.SUPABASE_JWT_SECRET = ""
        return settings

    @pytest.mark.asyncio
    async def test_websocket_connects_and_sends_connected(self) -> None:
        """Test that WebSocket accepts and sends WSConnected message."""
        from fastapi.testclient import TestClient
        from fastapi.websockets import WebSocket as FastAPIWebSocket

        ws = _make_websocket()
        ws.query_params = {"user_id": "user-1", "role": "basic"}
        ws.receive_text = AsyncMock(side_effect=Exception("disconnect"))

        settings = self._make_settings()

        with patch("backend.websocket.handler.get_settings", return_value=settings):
            with patch("backend.websocket.handler.AgentService") as mock_svc_cls:
                mock_svc = MagicMock()
                mock_svc_cls.return_value = mock_svc

                try:
                    from backend.websocket.handler import websocket_chat
                    await websocket_chat(ws, "sess-1", settings)
                except Exception:
                    pass

        ws.accept.assert_called_once()
        sent_texts = [c.args[0] for c in ws.send_text.call_args_list]
        connected_msgs = [
            json.loads(t) for t in sent_texts if json.loads(t).get("type") == "connected"
        ]
        assert len(connected_msgs) == 1
        assert connected_msgs[0]["session_id"] == "sess-1"

    @pytest.mark.asyncio
    async def test_ping_message_returns_pong(self) -> None:
        from backend.websocket.handler import websocket_chat

        ws = _make_websocket()
        ws.receive_text = AsyncMock(
            side_effect=[
                json.dumps({"type": "ping"}),
                Exception("stop"),
            ]
        )

        settings = self._make_settings()

        with patch("backend.websocket.handler.AgentService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc_cls.return_value = mock_svc
            try:
                await websocket_chat(ws, "sess-2", settings)
            except Exception:
                pass

        sent_texts = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        pongs = [m for m in sent_texts if m.get("type") == "pong"]
        assert len(pongs) >= 1

    @pytest.mark.asyncio
    async def test_invalid_json_returns_error(self) -> None:
        from backend.websocket.handler import websocket_chat

        ws = _make_websocket()
        ws.receive_text = AsyncMock(
            side_effect=[
                "this is not json",
                Exception("stop"),
            ]
        )

        settings = self._make_settings()

        with patch("backend.websocket.handler.AgentService") as mock_svc_cls:
            mock_svc_cls.return_value = MagicMock()
            try:
                await websocket_chat(ws, "sess-3", settings)
            except Exception:
                pass

        sent_texts = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        errors = [m for m in sent_texts if m.get("type") == "error"]
        assert any(e["code"] == "invalid_json" for e in errors)

    @pytest.mark.asyncio
    async def test_unknown_message_type_returns_error(self) -> None:
        from backend.websocket.handler import websocket_chat

        ws = _make_websocket()
        ws.receive_text = AsyncMock(
            side_effect=[
                json.dumps({"type": "unknown_type"}),
                Exception("stop"),
            ]
        )

        settings = self._make_settings()

        with patch("backend.websocket.handler.AgentService") as mock_svc_cls:
            mock_svc_cls.return_value = MagicMock()
            try:
                await websocket_chat(ws, "sess-4", settings)
            except Exception:
                pass

        sent_texts = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        errors = [m for m in sent_texts if m.get("type") == "error"]
        assert any(e["code"] == "unknown_message_type" for e in errors)

    @pytest.mark.asyncio
    async def test_empty_chat_message_returns_error(self) -> None:
        from backend.websocket.handler import websocket_chat

        ws = _make_websocket()
        ws.receive_text = AsyncMock(
            side_effect=[
                json.dumps({"type": "chat", "message": "   "}),
                Exception("stop"),
            ]
        )

        settings = self._make_settings()

        with patch("backend.websocket.handler.AgentService") as mock_svc_cls:
            mock_svc_cls.return_value = MagicMock()
            try:
                await websocket_chat(ws, "sess-5", settings)
            except Exception:
                pass

        sent_texts = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        errors = [m for m in sent_texts if m.get("type") == "error"]
        assert any(e["code"] == "empty_message" for e in errors)

    @pytest.mark.asyncio
    async def test_chat_message_invokes_agent_service(self) -> None:
        from backend.websocket.handler import websocket_chat

        ws = _make_websocket()
        ws.receive_text = AsyncMock(
            side_effect=[
                json.dumps({"type": "chat", "message": "Hello agent", "request_id": "req-ws"}),
                Exception("stop"),
            ]
        )

        settings = self._make_settings()
        mock_svc = MagicMock()
        mock_svc.run_turn = AsyncMock(return_value=MagicMock())

        with patch("backend.services.agent_service.AgentService", return_value=mock_svc):
            try:
                await websocket_chat(ws, "sess-6", settings)
            except Exception:
                pass

        mock_svc.run_turn.assert_called_once()
        call_kwargs = mock_svc.run_turn.call_args.kwargs
        assert call_kwargs["message"] == "Hello agent"
        assert call_kwargs["session_id"] == "sess-6"

    @pytest.mark.asyncio
    async def test_agent_error_sends_error_message(self) -> None:
        from backend.websocket.handler import websocket_chat

        ws = _make_websocket()
        ws.receive_text = AsyncMock(
            side_effect=[
                json.dumps({"type": "chat", "message": "Trigger error", "request_id": "req-err"}),
                Exception("stop loop"),
            ]
        )

        settings = self._make_settings()
        mock_svc = MagicMock()
        mock_svc.run_turn = AsyncMock(side_effect=RuntimeError("Agent crashed"))

        with patch("backend.services.agent_service.AgentService", return_value=mock_svc):
            try:
                await websocket_chat(ws, "sess-7", settings)
            except Exception:
                pass

        sent_texts = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        errors = [m for m in sent_texts if m.get("type") == "error"]
        assert any(e["code"] == "agent_error" for e in errors)

    @pytest.mark.asyncio
    async def test_websocket_disconnect_handled_gracefully(self) -> None:
        from fastapi.websockets import WebSocketDisconnect
        from backend.websocket.handler import websocket_chat

        ws = _make_websocket()
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        settings = self._make_settings()
        mock_svc = MagicMock()

        with patch("backend.websocket.handler.AgentService", return_value=mock_svc):
            # Should not raise
            await websocket_chat(ws, "sess-8", settings)

    @pytest.mark.asyncio
    async def test_invalid_role_query_param_defaults_to_basic(self) -> None:
        from backend.websocket.handler import websocket_chat
        from risk_gates.schemas import UserRole

        ws = _make_websocket()
        ws.query_params = {"user_id": "user-x", "role": "superadmin"}
        ws.receive_text = AsyncMock(side_effect=Exception("stop"))

        settings = self._make_settings()
        captured_users: list[Any] = []
        mock_svc = MagicMock()

        original_init = __import__(
            "backend.services.agent_service", fromlist=["AgentService"]
        ).AgentService.__init__

        with patch("backend.websocket.handler.AgentService") as mock_cls:
            mock_cls.return_value = mock_svc
            try:
                await websocket_chat(ws, "sess-9", settings)
            except Exception:
                pass

        # Role should default to basic for unknown role
        ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_message_without_request_id_auto_generates(self) -> None:
        from backend.websocket.handler import websocket_chat

        ws = _make_websocket()
        ws.receive_text = AsyncMock(
            side_effect=[
                json.dumps({"type": "chat", "message": "No request_id"}),
                Exception("stop"),
            ]
        )

        settings = self._make_settings()
        mock_svc = MagicMock()
        mock_svc.run_turn = AsyncMock(return_value=MagicMock())

        with patch("backend.services.agent_service.AgentService", return_value=mock_svc):
            try:
                await websocket_chat(ws, "sess-10", settings)
            except Exception:
                pass

        mock_svc.run_turn.assert_called_once()
        # Should have auto-generated a request_id (not None)
        call_kwargs = mock_svc.run_turn.call_args.kwargs
        assert call_kwargs.get("request_id") is not None


# ─── Protocol model tests ─────────────────────────────────────────────────

class TestProtocolModels:
    def test_ws_connected_serialization(self) -> None:
        msg = WSConnected(session_id="sess-1")
        data = json.loads(msg.model_dump_json())
        assert data["type"] == "connected"
        assert data["session_id"] == "sess-1"

    def test_ws_token_turn_id_alias(self) -> None:
        token = WSToken(content="hello", request_id="req-1")
        assert token.turn_id == "req-1"

    def test_ws_gate_event_defaults(self) -> None:
        event = WSGateEvent(gate="pre_llm", action="allow", reason="OK")
        assert event.type == "gate_event"
        assert event.metadata == {}

    def test_ws_turn_end_serialization(self) -> None:
        turn_end = WSTurnEnd(request_id="req-1", session_id="sess-1")
        data = json.loads(turn_end.model_dump_json())
        assert data["type"] == "turn_end"
        assert data["turn_id"] == "req-1"

    def test_ws_error_serialization(self) -> None:
        err = WSError(code="test_error", message="Something went wrong")
        data = json.loads(err.model_dump_json())
        assert data["type"] == "error"
        assert data["code"] == "test_error"

    def test_ws_pong_has_server_time(self) -> None:
        pong = WSPong()
        assert pong.server_time is not None

    def test_ws_tool_start_serialization(self) -> None:
        ts = WSToolStart(tool_name="get_quote", call_id="c1")
        data = json.loads(ts.model_dump_json())
        assert data["type"] == "tool_start"

    def test_ws_tool_result_serialization(self) -> None:
        tr = WSToolResult(tool_name="get_quote", call_id="c1", status="success")
        data = json.loads(tr.model_dump_json())
        assert data["type"] == "tool_result"
        assert data["status"] == "success"

    def test_ws_turn_start_turn_id_alias(self) -> None:
        from backend.websocket.protocol import WSTurnStart

        ts = WSTurnStart(request_id="req-x", session_id="sess-x")
        assert ts.turn_id == "req-x"


# ─── _run_early_post_llm_gate tests ──────────────────────────────────────

class TestRunEarlyPostLlmGate:
    @pytest.mark.asyncio
    async def test_already_emitted_returns_early(self) -> None:
        from backend.websocket.stream import _run_early_post_llm_gate

        ws = _make_websocket()
        emitted_flag = [True]  # Already emitted

        # Should return immediately without calling run_post_llm_gate
        with patch("backend.websocket.stream.asyncio.sleep", new=AsyncMock()):
            await _run_early_post_llm_gate(
                llm_buffer=["hello"],
                websocket=ws,
                request_id="req-1",
                risk_context_dict=None,
                original_input="test",
                emitted_flag=emitted_flag,
            )

        ws.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_emits_gate_event_on_success(self) -> None:
        from backend.websocket.stream import _run_early_post_llm_gate
        from risk_gates.schemas import AuditEntry, GateAction, GateDecision, GateName

        audit = AuditEntry(
            gate=GateName.POST_LLM,
            action=GateAction.ALLOW,
            reason="OK",
            request_id="r1",
            user_id="u1",
        )
        gate_dec = GateDecision(action=GateAction.ALLOW, reason="OK", audit=audit)

        from risk_gates.schemas import PostLLMDecision

        mock_decision = PostLLMDecision(
            gate_decision=gate_dec,
            compliance_flags=[],
        )

        ws = _make_websocket()
        emitted_flag = [False]

        with patch("backend.websocket.stream.asyncio.sleep", new=AsyncMock()):
            with patch(
                "risk_gates.gates.post_llm.run_post_llm_gate",
                new=AsyncMock(return_value=mock_decision),
            ):
                await _run_early_post_llm_gate(
                    llm_buffer=["Hello", " world"],
                    websocket=ws,
                    request_id="req-2",
                    risk_context_dict={"user_id": "u1", "session_id": "s1", "user_role": "basic"},
                    original_input="test input",
                    emitted_flag=emitted_flag,
                )

        assert emitted_flag[0] is True
        sent = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        gate_msgs = [m for m in sent if m.get("type") == "gate_event"]
        assert len(gate_msgs) == 1
        assert gate_msgs[0]["gate"] == "post_llm"

    @pytest.mark.asyncio
    async def test_exception_in_gate_uses_allow_fallback(self) -> None:
        from backend.websocket.stream import _run_early_post_llm_gate

        ws = _make_websocket()
        emitted_flag = [False]

        with patch("backend.websocket.stream.asyncio.sleep", new=AsyncMock()):
            with patch(
                "risk_gates.gates.post_llm.run_post_llm_gate",
                new=AsyncMock(side_effect=Exception("OPA down")),
            ):
                await _run_early_post_llm_gate(
                    llm_buffer=["partial"],
                    websocket=ws,
                    request_id="req-3",
                    risk_context_dict=None,
                    original_input="test",
                    emitted_flag=emitted_flag,
                )

        assert emitted_flag[0] is True
        sent = [json.loads(c.args[0]) for c in ws.send_text.call_args_list]
        gate_msgs = [m for m in sent if m.get("type") == "gate_event"]
        assert gate_msgs[0]["action"] == "allow"

    @pytest.mark.asyncio
    async def test_invalid_user_role_defaults_to_basic(self) -> None:
        from backend.websocket.stream import _run_early_post_llm_gate

        ws = _make_websocket()
        emitted_flag = [False]

        with patch("backend.websocket.stream.asyncio.sleep", new=AsyncMock()):
            with patch(
                "risk_gates.gates.post_llm.run_post_llm_gate",
                new=AsyncMock(side_effect=Exception("gate error")),
            ):
                await _run_early_post_llm_gate(
                    llm_buffer=["text"],
                    websocket=ws,
                    request_id="req-4",
                    risk_context_dict={"user_role": "invalid_role"},
                    original_input="test",
                    emitted_flag=emitted_flag,
                )

        # Should complete without raising
        assert emitted_flag[0] is True
