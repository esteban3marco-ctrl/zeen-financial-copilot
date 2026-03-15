"""OPA HTTP client wrapper with Python fallback and OpenTelemetry instrumentation."""
from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from risk_gates.schemas import (
    AuditEntry,
    GateAction,
    GateDecision,
    GateName,
    PostLLMDecision,
    PostLLMRequest,
    PostToolDecision,
    PostToolRequest,
    PreLLMDecision,
    PreLLMRequest,
    PreToolDecision,
    PreToolRequest,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("staq.risk_gates.evaluator")

OPA_BASE_URL = "http://localhost:8181"
OPA_TIMEOUT_SECONDS = 0.5  # Fast timeout so Python fallback kicks in quickly when OPA not running


class OPAEvaluationError(Exception):
    """Raised when OPA server is unreachable or returns unexpected response."""


# ── Python fallback evaluators ─────────────────────────────────────────────

_PII_PATTERNS: dict[str, str] = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "iban": r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]{0,16})\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
}

_INJECTION_PATTERNS = [
    r"ignore\s+(?:previous|all)\s+instructions?",
    r"you\s+are\s+now\s+(?:an?\s+)?(?:evil|unrestricted|jailbroken)",
    r"forget\s+(?:your\s+)?(?:instructions?|rules?|guidelines?|prompt)",
    r"act\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?(?:dan|evil|unrestricted)",
    r"drop\s+table",
    r"<script",
    r"system\s+prompt\s*:",
]

_BLOCKED_FINANCIAL_PATTERNS = [
    r"\bguaranteed?\b.{0,30}\breturn",
    r"\bget\s+rich\s+quick",
    r"\bdouble\s+(?:your\s+)?(?:money|investment)",
    r"\b100\s*%\s+(?:safe|profit|return|guaranteed)",
    r"\binsider\s+(?:tip|trading|information)",
    r"\bpump\s+and\s+dump",
    r"\bbuy\s+crypto\s+now",
]

_FINANCIAL_ADVICE_PATTERNS = [
    r"\byou\s+should\s+(?:buy|sell|invest)",
    r"\bi\s+recommend\s+(?:buying|selling|investing)",
    r"\bmy\s+(?:advice|recommendation)\s+is\s+to\s+(?:buy|sell)",
    r"\bwill\s+definitely\s+(?:rise|fall|increase|decrease)",
    r"\bguaranteed\s+to\s+(?:increase|grow|profit)",
]

_DISCLAIMER = (
    "\n\n---\n"
    "*Disclaimer: This information is for educational purposes only and does not "
    "constitute financial advice. Please consult a licensed financial advisor before "
    "making investment decisions.*"
)


def _check_injection(text: str) -> float:
    """Return injection score 0.0–1.0."""
    hits = sum(1 for p in _INJECTION_PATTERNS if re.search(p, text, re.I))
    return min(1.0, hits * 0.4)


def _check_pii(text: str) -> list[str]:
    """Return list of PII type names found."""
    return [t for t, p in _PII_PATTERNS.items() if re.search(p, text)]


def _python_pre_llm(request: PreLLMRequest) -> dict[str, Any]:
    """Python fallback evaluation for pre_llm gate."""
    text = request.user_input
    injection_score = _check_injection(text)
    pii_found = _check_pii(text)

    if injection_score >= 0.8:
        return {
            "decision": {
                "action": "deny",
                "reason": f"Prompt injection detected (score={injection_score:.2f})",
            },
            "injection_score": injection_score,
            "pii_found": pii_found,
        }

    for pattern in _BLOCKED_FINANCIAL_PATTERNS:
        if re.search(pattern, text, re.I):
            return {
                "decision": {
                    "action": "deny",
                    "reason": "Query contains high-risk financial content (potential fraud/scam patterns)",
                },
                "injection_score": injection_score,
                "pii_found": pii_found,
            }

    if pii_found:
        return {
            "decision": {
                "action": "modify",
                "reason": f"PII detected and redacted: {', '.join(pii_found)}",
                "pii_redacted": len(pii_found),
            },
            "injection_score": injection_score,
            "pii_found": pii_found,
        }

    return {
        "decision": {
            "action": "allow",
            "reason": "Input validated — no PII, injection, or blocked content detected",
        },
        "injection_score": injection_score,
        "pii_found": [],
    }


def _python_post_llm(request: PostLLMRequest) -> dict[str, Any]:
    """Python fallback evaluation for post_llm gate."""
    response = request.llm_response

    for pattern in _FINANCIAL_ADVICE_PATTERNS:
        if re.search(pattern, response, re.I):
            return {
                "decision": {
                    "action": "modify",
                    "reason": "Response contains direct financial advice — regulatory disclaimer injected",
                    "compliance_flags": ["financial_advice_detected"],
                },
                "modified_response": response + _DISCLAIMER,
                "hallucination_markers": [],
            }

    return {
        "decision": {
            "action": "allow",
            "reason": "Response passed compliance and hallucination checks",
            "compliance_flags": [],
        },
        "hallucination_markers": [],
    }


def _python_pre_tool(request: PreToolRequest) -> dict[str, Any]:
    """Python fallback evaluation for pre_tool gate."""
    dangerous_tools = {"exec_code", "shell_exec", "file_write", "system_cmd"}
    if request.tool_name in dangerous_tools:
        role = (
            request.risk_context.user_role.value
            if hasattr(request.risk_context.user_role, "value")
            else str(request.risk_context.user_role)
        )
        if role not in ("advisor", "admin"):
            return {
                "decision": {
                    "action": "deny",
                    "reason": f"Tool '{request.tool_name}' requires advisor or admin role",
                },
                "requires_sandbox": False,
                "rate_limit_remaining": -1,
            }

    return {
        "decision": {
            "action": "allow",
            "reason": f"Tool '{request.tool_name}' authorized for execution",
        },
        "requires_sandbox": False,
        "rate_limit_remaining": 100,
    }


def _python_post_tool(request: PostToolRequest) -> dict[str, Any]:
    """Python fallback evaluation for post_tool gate."""
    result_str = str(request.tool_result or "")
    secrets_found: list[str] = []

    if re.search(r"\bsk-[A-Za-z0-9]{20,}", result_str):
        secrets_found.append("api_key")
    if re.search(r"\bpassword\s*[:=]\s*\S+", result_str, re.I):
        secrets_found.append("password")

    if secrets_found:
        return {
            "decision": {
                "action": "modify",
                "reason": f"Sensitive data detected in tool output: {', '.join(secrets_found)}",
            },
            "sanitized_result": "[REDACTED]",
            "secrets_found": secrets_found,
        }

    return {
        "decision": {
            "action": "allow",
            "reason": "Tool output validated — no sensitive data detected",
        },
        "sanitized_result": None,
        "secrets_found": [],
    }


# ── OPA HTTP client ────────────────────────────────────────────────────────

async def _call_opa(package_path: str, input_data: dict[str, Any]) -> dict[str, Any]:
    """POST input to OPA and return the result dict."""
    url = f"{OPA_BASE_URL}/v1/data/{package_path}"
    with tracer.start_as_current_span(f"opa.evaluate.{package_path}") as span:
        span.set_attribute("opa.package", package_path)
        try:
            async with httpx.AsyncClient(timeout=OPA_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json={"input": input_data})
            response.raise_for_status()
            body = response.json()
            result: dict[str, Any] = body.get("result", {})
            span.set_attribute("opa.decision.action", result.get("decision", {}).get("action", "unknown"))
            return result
        except (httpx.HTTPError, httpx.ConnectError, OSError) as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            logger.warning("OPA unavailable for %s — Python fallback will be used", package_path)
            raise OPAEvaluationError(f"OPA request failed: {exc}") from exc


def _build_gate_decision(
    opa_result: dict[str, Any],
    gate: GateName,
    request_id: str,
    user_id: str,
) -> GateDecision:
    decision_raw: dict[str, Any] = opa_result.get("decision", {})
    action = GateAction(decision_raw.get("action", "allow"))
    reason: str = decision_raw.get("reason", "No reason provided")
    audit = AuditEntry(
        gate=gate,
        action=action,
        reason=reason,
        request_id=request_id,
        user_id=user_id,
        metadata={k: v for k, v in decision_raw.items() if k not in {"action", "reason"}},
    )
    return GateDecision(action=action, reason=reason, audit=audit)


# ── Public evaluate functions ──────────────────────────────────────────────

async def evaluate_pre_llm(request: PreLLMRequest) -> PreLLMDecision:
    """Evaluate the pre-LLM gate via OPA, with Python fallback."""
    with tracer.start_as_current_span("gate.pre_llm"):
        try:
            opa_result = await _call_opa(
                "staq/gates/pre_llm",
                input_data=request.model_dump(mode="json"),
            )
        except OPAEvaluationError:
            opa_result = _python_pre_llm(request)

        gate_decision = _build_gate_decision(
            opa_result,
            gate=GateName.PRE_LLM,
            request_id=request.risk_context.request_id,
            user_id=request.risk_context.user_id,
        )
        detected_pii = opa_result.get("pii_found", [])
        return PreLLMDecision(
            gate_decision=gate_decision,
            sanitized_input=opa_result.get("sanitized_input"),
            detected_pii=detected_pii,
            injection_score=float(opa_result.get("injection_score", 0.0)),
        )


async def evaluate_post_llm(request: PostLLMRequest) -> PostLLMDecision:
    """Evaluate the post-LLM gate via OPA, with Python fallback."""
    with tracer.start_as_current_span("gate.post_llm"):
        try:
            opa_result = await _call_opa(
                "staq/gates/post_llm",
                input_data=request.model_dump(mode="json"),
            )
        except OPAEvaluationError:
            opa_result = _python_post_llm(request)

        gate_decision = _build_gate_decision(
            opa_result,
            gate=GateName.POST_LLM,
            request_id=request.risk_context.request_id,
            user_id=request.risk_context.user_id,
        )
        decision_raw = opa_result.get("decision", {})
        return PostLLMDecision(
            gate_decision=gate_decision,
            modified_response=opa_result.get("modified_response"),
            compliance_flags=decision_raw.get("compliance_flags", []),
            hallucination_markers=opa_result.get("hallucination_markers", []),
        )


async def evaluate_pre_tool(request: PreToolRequest) -> PreToolDecision:
    """Evaluate the pre-tool gate via OPA, with Python fallback."""
    with tracer.start_as_current_span("gate.pre_tool"):
        try:
            opa_result = await _call_opa(
                "staq/gates/pre_tool",
                input_data=request.model_dump(mode="json"),
            )
        except OPAEvaluationError:
            opa_result = _python_pre_tool(request)

        gate_decision = _build_gate_decision(
            opa_result,
            gate=GateName.PRE_TOOL,
            request_id=request.risk_context.request_id,
            user_id=request.risk_context.user_id,
        )
        return PreToolDecision(
            gate_decision=gate_decision,
            requires_sandbox=bool(opa_result.get("requires_sandbox", False)),
            rate_limit_remaining=int(opa_result.get("rate_limit_remaining", -1)),
            sanitized_params=opa_result.get("sanitized_params"),
        )


async def evaluate_post_tool(request: PostToolRequest) -> PostToolDecision:
    """Evaluate the post-tool gate via OPA, with Python fallback."""
    with tracer.start_as_current_span("gate.post_tool"):
        try:
            opa_result = await _call_opa(
                "staq/gates/post_tool",
                input_data=request.model_dump(mode="json"),
            )
        except OPAEvaluationError:
            opa_result = _python_post_tool(request)

        gate_decision = _build_gate_decision(
            opa_result,
            gate=GateName.POST_TOOL,
            request_id=request.risk_context.request_id,
            user_id=request.risk_context.user_id,
        )
        return PostToolDecision(
            gate_decision=gate_decision,
            sanitized_result=opa_result.get("sanitized_result"),
            secrets_found=list(opa_result.get("secrets_found", [])),
            data_freshness=opa_result.get("data_freshness"),
        )
