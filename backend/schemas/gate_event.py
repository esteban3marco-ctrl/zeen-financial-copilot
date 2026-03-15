"""Gate event output schema."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class GateEventOut(BaseModel):
    gate: str       # "pre_llm" | "post_llm" | "pre_tool" | "post_tool"
    action: str     # "allow" | "deny" | "modify"
    reason: str
    fired_at: datetime
    metadata: dict[str, Any] = {}
