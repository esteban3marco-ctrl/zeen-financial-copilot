"""Session management router."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.middleware import get_current_user
from backend.auth.models import AuthUser
from backend.schemas.session import SessionListResponse, SessionOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    user_id: str | None = None


@router.post("", response_model=SessionOut, status_code=201)
async def create_session(
    body: CreateSessionRequest,
    auth_user: Annotated[AuthUser, Depends(get_current_user)],
) -> SessionOut:
    now = datetime.now(timezone.utc)
    return SessionOut(
        session_id=str(uuid.uuid4()),
        user_id=auth_user.user_id or body.user_id or "demo-user",
        turn_count=0,
        total_tokens=0,
        status="active",
        created_at=now,
        updated_at=now,
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    auth_user: Annotated[AuthUser, Depends(get_current_user)],
) -> SessionListResponse:
    """List all sessions for the authenticated user."""
    try:
        from memory.conversation import load_conversation
        import os
        from supabase import create_client

        client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        result = (
            client.table("conversations")
            .select("id, session_id, user_id, turn_count, total_tokens, status, created_at, updated_at")
            .eq("user_id", auth_user.user_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        sessions = [
            SessionOut(
                session_id=cast(dict[str, Any], row)["session_id"],
                user_id=cast(dict[str, Any], row)["user_id"],
                turn_count=cast(dict[str, Any], row).get("turn_count", 0),
                total_tokens=cast(dict[str, Any], row).get("total_tokens", 0),
                status=cast(dict[str, Any], row).get("status", "active"),
                created_at=cast(dict[str, Any], row).get("created_at"),
                updated_at=cast(dict[str, Any], row).get("updated_at"),
            )
            for row in (result.data or [])
        ]
        return SessionListResponse(sessions=sessions, total=len(sessions))
    except KeyError:
        logger.warning("Supabase not configured â€” returning empty session list")
        return SessionListResponse(sessions=[], total=0)
    except Exception as exc:
        logger.error("Failed to list sessions: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: str,
    auth_user: Annotated[AuthUser, Depends(get_current_user)],
) -> SessionOut:
    """Get a single session by ID."""
    try:
        import os
        from supabase import create_client

        client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        result = (
            client.table("conversations")
            .select("id, session_id, user_id, turn_count, total_tokens, status, created_at, updated_at")
            .eq("session_id", session_id)
            .eq("user_id", auth_user.user_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Session not found")

        row: dict[str, Any] = cast(dict[str, Any], result.data)
        return SessionOut(
            session_id=row["session_id"],
            user_id=row["user_id"],
            turn_count=row.get("turn_count", 0),
            total_tokens=row.get("total_tokens", 0),
            status=row.get("status", "active"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
    except HTTPException:
        raise
    except KeyError:
        raise HTTPException(status_code=503, detail="Database not configured")
    except Exception as exc:
        logger.error("Failed to get session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    auth_user: Annotated[AuthUser, Depends(get_current_user)],
) -> None:
    """Delete a session (soft-delete by setting status to 'deleted')."""
    try:
        import os
        from supabase import create_client

        client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        result = (
            client.table("conversations")
            .update({"status": "deleted"})
            .eq("session_id", session_id)
            .eq("user_id", auth_user.user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except KeyError:
        raise HTTPException(status_code=503, detail="Database not configured")
    except Exception as exc:
        logger.error("Failed to delete session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete session")
