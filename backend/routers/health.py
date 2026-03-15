"""Health check router."""
from __future__ import annotations

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from backend.config import Settings, get_settings

router = APIRouter(prefix="/health", tags=["health"])

_START_TIME = time.time()


@router.get("")
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
    return {
        "status": "ok",
        "demo_mode": settings.DEMO_MODE,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    }


@router.get("/ready")
async def readiness(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
    checks: dict[str, str] = {}

    # Check OPA reachability
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.OPA_URL}/health")
            checks["opa"] = "ok" if resp.status_code == 200 else f"http_{resp.status_code}"
    except Exception as exc:
        checks["opa"] = f"unreachable: {exc}"

    # Check Supabase config
    checks["supabase"] = "configured" if settings.SUPABASE_URL else "not_configured"

    all_ok = all(v in ("ok", "configured") for v in checks.values())
    return {
        "ready": all_ok,
        "checks": checks,
    }
