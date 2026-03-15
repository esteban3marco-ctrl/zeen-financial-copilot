"""Tool event output schema."""
from __future__ import annotations

from pydantic import BaseModel


class ToolEventOut(BaseModel):
    tool_name: str
    call_id: str
    status: str             # "success" | "error" | "denied" | "timeout"
    sandbox_used: bool
    execution_time_ms: float
    result_preview: str | None = None
