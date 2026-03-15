"""Chat HTTP router."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.auth.middleware import get_current_user
from backend.auth.models import AuthUser
from backend.dependencies import get_agent_service
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.agent_service import AgentService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    auth_user: Annotated[AuthUser, Depends(get_current_user)],
    agent_svc: Annotated[AgentService, Depends(get_agent_service)],
) -> ChatResponse:
    """Send a message to the Financial Copilot agent and receive a full response."""
    session_id = req.session_id or str(uuid.uuid4())

    # Allow ChatRequest to carry a role override (useful for demos)
    effective_user = auth_user
    if req.user_role != auth_user.user_role:
        effective_user = auth_user.model_copy(update={"user_role": req.user_role})

    return await agent_svc.run_turn(
        message=req.message,
        session_id=session_id,
        auth_user=effective_user,
    )
