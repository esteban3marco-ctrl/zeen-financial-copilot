"""FastAPI dependency providers."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from backend.config import Settings, get_settings
from backend.services.agent_service import AgentService

_agent_service_instance: AgentService | None = None


def get_agent_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentService:
    global _agent_service_instance
    if _agent_service_instance is None:
        try:
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()
        except Exception:
            checkpointer = None  # type: ignore[assignment]
        _agent_service_instance = AgentService(settings=settings, checkpointer=checkpointer)
    return _agent_service_instance
