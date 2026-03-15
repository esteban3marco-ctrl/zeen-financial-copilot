"""Demo scenario router."""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.models import AuthUser
from backend.dependencies import get_agent_service
from backend.schemas.chat import ChatResponse
from backend.services.agent_service import AgentService
from backend.services.scenario_service import SCENARIOS

router = APIRouter(prefix="/demo", tags=["demo"])


class ScenarioRequest(BaseModel):
    scenario_id: str
    session_id: str | None = None


class ScenarioResponse(BaseModel):
    session_id: str
    injected_message: str
    expected_behavior: str
    risk_level: str
    chat_response: ChatResponse


@router.get("/scenarios")
async def list_scenarios() -> dict[str, Any]:
    """List all available demo scenarios."""
    return {
        "scenarios": [
            {
                "scenario_id": s.scenario_id,
                "description": s.description,
                "risk_level": s.risk_level,
                "role": s.role.value,
            }
            for s in SCENARIOS.values()
        ]
    }


@router.post("/scenario", response_model=ScenarioResponse)
async def run_scenario(
    req: ScenarioRequest,
    agent_svc: Annotated[AgentService, Depends(get_agent_service)],
) -> ScenarioResponse:
    """Run a predefined demo scenario through the agent."""
    scenario = SCENARIOS.get(req.scenario_id)
    if scenario is None:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{req.scenario_id}' not found. "
            f"Available: {list(SCENARIOS.keys())}",
        )

    session_id = req.session_id or str(uuid.uuid4())
    auth_user = AuthUser(
        user_id="demo",
        email="demo@staq.ai",
        user_role=scenario.role,
        demo_mode=True,
    )

    response = await agent_svc.run_turn(
        message=scenario.message,
        session_id=session_id,
        auth_user=auth_user,
    )

    return ScenarioResponse(
        session_id=response.session_id,
        injected_message=scenario.message,
        expected_behavior=scenario.description,
        risk_level=scenario.risk_level,
        chat_response=response,
    )
