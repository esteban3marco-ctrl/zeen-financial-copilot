"""Pre-LLM gate: PII redaction and injection scoring applied after OPA decision."""
from __future__ import annotations

import re

from opentelemetry import trace

from risk_gates.schemas import (
    GateAction,
    PIIMatch,
    PreLLMDecision,
    PreLLMRequest,
)
from risk_gates.evaluator import evaluate_pre_llm

tracer = trace.get_tracer("staq.risk_gates.gates.pre_llm")

_PII_PATTERNS: dict[str, str] = {
    "ssn": r"\b(\d{3})-(\d{2})-(\d{4})\b",
    "credit_card": r"\b(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})\b",
    "iban": r"\b([A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]{0,16}))\b",
    "email": r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b",
}


def _redact_pii(text: str) -> tuple[str, list[PIIMatch]]:
    """Redact PII from text and return sanitized text + matches."""
    matches: list[PIIMatch] = []
    result = text
    offset = 0

    for pii_type, pattern in _PII_PATTERNS.items():
        for m in re.finditer(pattern, result):
            original = m.group(0)
            if pii_type == "ssn":
                redacted = f"***-**-{m.group(3)}"
            elif pii_type == "credit_card":
                redacted = f"****-****-****-{m.group(4)}"
            elif pii_type == "email":
                local, domain = original.rsplit("@", 1)
                redacted = f"{local[:2]}***@{domain}"
            else:
                redacted = f"[REDACTED_{pii_type.upper()}]"

            matches.append(
                PIIMatch(
                    pii_type=pii_type,
                    start_index=m.start() + offset,
                    end_index=m.end() + offset,
                    redacted_value=redacted,
                )
            )
            result = result[: m.start()] + redacted + result[m.end() :]
            offset += len(redacted) - len(original)

    return result, matches


async def run_pre_llm_gate(request: PreLLMRequest) -> PreLLMDecision:
    """Full pre-LLM gate: OPA evaluation + Python-side PII redaction."""
    with tracer.start_as_current_span("gate.pre_llm.run"):
        decision = await evaluate_pre_llm(request)

        if decision.gate_decision.action == GateAction.MODIFY:
            sanitized, pii_matches = _redact_pii(request.user_input)
            return PreLLMDecision(
                gate_decision=decision.gate_decision,
                sanitized_input=sanitized,
                detected_pii=pii_matches,
                injection_score=decision.injection_score,
            )

        return decision
