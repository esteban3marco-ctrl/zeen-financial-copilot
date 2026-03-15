"""WebSocket chat endpoint."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from backend.auth.middleware import get_current_user
from backend.auth.models import AuthUser
from backend.config import Settings, get_settings
from backend.dependencies import get_agent_service
from backend.services.agent_service import AgentService
from backend.websocket.protocol import (
    WSConnected,
    WSError,
    WSPong,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """WebSocket endpoint for streaming chat with the Financial Copilot agent."""
    await websocket.accept()

    # Build a synthetic AuthUser from query params / headers since HTTP
    # dependency injection does not work directly in WS endpoints.
    from backend.auth.models import AuthUser
    from risk_gates.schemas import UserRole

    demo_role_raw = websocket.query_params.get("role", "basic")
    try:
        ws_role = UserRole(demo_role_raw.lower())
    except ValueError:
        ws_role = UserRole.BASIC

    auth_user = AuthUser(
        user_id=websocket.query_params.get("user_id", "demo-user"),
        email=websocket.query_params.get("email"),
        user_role=ws_role,
        demo_mode=settings.DEMO_MODE,
    )

    # Instantiate AgentService con InMemorySaver (fallback sin Supabase)
    try:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
    except Exception:
        checkpointer = None  # type: ignore[assignment]

    from backend.services.agent_service import AgentService
    agent_svc = AgentService(settings=settings, checkpointer=checkpointer)

    # Send connected acknowledgement
    connected_msg = WSConnected(session_id=session_id)
    await websocket.send_text(connected_msg.model_dump_json())

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                err = WSError(
                    code="invalid_json",
                    message="Message must be valid JSON",
                )
                await websocket.send_text(err.model_dump_json())
                continue

            msg_type = payload.get("type", "")

            if msg_type == "ping":
                pong = WSPong()
                await websocket.send_text(pong.model_dump_json())
                continue

            if msg_type == "chat":
                message_text: str = payload.get("message", "").strip()
                request_id: str = payload.get("request_id") or str(uuid.uuid4())

                if not message_text:
                    err = WSError(
                        code="empty_message",
                        message="message field must not be empty",
                        request_id=request_id,
                    )
                    await websocket.send_text(err.model_dump_json())
                    continue

                try:
                    await agent_svc.run_turn(
                        message=message_text,
                        session_id=session_id,
                        auth_user=auth_user,
                        websocket=websocket,
                        request_id=request_id,
                    )
                except Exception as exc:
                    logger.exception(
                        "Agent error for session=%s request_id=%s: %s",
                        session_id,
                        request_id,
                        exc,
                    )
                    err = WSError(
                        code="agent_error",
                        message=str(exc),
                        request_id=request_id,
                    )
                    await websocket.send_text(err.model_dump_json())

            else:
                err = WSError(
                    code="unknown_message_type",
                    message=f"Unknown message type: {msg_type!r}",
                )
                await websocket.send_text(err.model_dump_json())

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: session=%s", session_id)
    except Exception as exc:
        logger.exception("Unexpected WebSocket error: session=%s %s", session_id, exc)
        try:
            err = WSError(code="internal_error", message="Internal server error")
            await websocket.send_text(err.model_dump_json())
        except Exception:
            pass
