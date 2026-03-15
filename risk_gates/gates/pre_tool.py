"""Pre-tool gate: parameter sanitization after OPA authorization."""
from __future__ import annotations

import html
import re
from typing import Any

from opentelemetry import trace

from risk_gates.schemas import (
    GateAction,
    PreToolDecision,
    PreToolRequest,
)
from risk_gates.evaluator import evaluate_pre_tool

tracer = trace.get_tracer("staq.risk_gates.gates.pre_tool")


def _sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    """Escape HTML and strip control characters from string param values."""
    sanitized = {}
    for key, value in params.items():
        if isinstance(value, str):
            clean = re.sub(r"[\x00-\x1f\x7f]", "", value)
            sanitized[key] = html.escape(clean)
        else:
            sanitized[key] = value
    return sanitized


async def run_pre_tool_gate(request: PreToolRequest) -> PreToolDecision:
    """Full pre-tool gate: OPA evaluation + Python-side param sanitization."""
    with tracer.start_as_current_span("gate.pre_tool.run"):
        decision = await evaluate_pre_tool(request)

        if decision.gate_decision.action == GateAction.ALLOW and request.tool_params:
            sanitized = _sanitize_params(request.tool_params)
            return PreToolDecision(
                gate_decision=decision.gate_decision,
                requires_sandbox=decision.requires_sandbox,
                rate_limit_remaining=decision.rate_limit_remaining,
                sanitized_params=sanitized,
            )

        return decision
