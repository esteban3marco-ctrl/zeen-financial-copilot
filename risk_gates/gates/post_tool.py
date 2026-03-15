"""Post-tool gate: secret redaction and data truncation."""
from __future__ import annotations

import re
from typing import Any

from opentelemetry import trace

from risk_gates.schemas import (
    GateAction,
    PostToolDecision,
    PostToolRequest,
)
from risk_gates.evaluator import evaluate_post_tool

tracer = trace.get_tracer("staq.risk_gates.gates.post_tool")

_SECRET_PATTERNS: dict[str, str] = {
    "api_key": r"(?i)(api[_-]?key|apikey)\s*[:=]\s*([A-Za-z0-9_\-]{20,})",
    "bearer_token": r"(?i)(bearer\s+)([A-Za-z0-9_\-\.]{20,})",
    "aws_key": r"(AKIA[0-9A-Z]{16})",
    "password": r"(?i)(password|passwd|pwd)\s*[:=]\s*(\S{6,})",
    "supabase_key": r"(eyJ[A-Za-z0-9_\-]{30,}\.[A-Za-z0-9_\-]{30,})",
}

_MAX_ROWS = 500


def _redact_secrets(text: str) -> tuple[str, list[str]]:
    """Replace secrets in text with redaction markers."""
    redacted = text
    found: list[str] = []
    for secret_type, pattern in _SECRET_PATTERNS.items():
        if re.search(pattern, redacted):
            found.append(secret_type)
            def _replacer(m: re.Match[str], st: str = secret_type) -> str:
                return f"[REDACTED_{st.upper()}]"
            redacted = re.sub(pattern, _replacer, redacted)
    return redacted, found


def _truncate_result(result: Any) -> Any:
    """Truncate list/rows results to MAX_ROWS."""
    if isinstance(result, list) and len(result) > _MAX_ROWS:
        return result[:_MAX_ROWS]
    if isinstance(result, dict) and isinstance(result.get("rows"), list):
        result = dict(result)
        result["rows"] = result["rows"][:_MAX_ROWS]
        result["truncated"] = True
    return result


async def run_post_tool_gate(request: PostToolRequest) -> PostToolDecision:
    """Full post-tool gate: OPA evaluation + Python-side sanitization."""
    with tracer.start_as_current_span("gate.post_tool.run"):
        decision = await evaluate_post_tool(request)

        if decision.gate_decision.action == GateAction.MODIFY:
            result_str = str(request.tool_result)
            sanitized_str, found = _redact_secrets(result_str)
            truncated = _truncate_result(request.tool_result)
            return PostToolDecision(
                gate_decision=decision.gate_decision,
                sanitized_result=truncated if not found else sanitized_str,
                secrets_found=found or decision.secrets_found,
                data_freshness=decision.data_freshness,
            )

        return decision
