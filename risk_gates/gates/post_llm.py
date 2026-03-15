"""Post-LLM gate: disclaimer injection and hallucination flagging."""
from __future__ import annotations

from opentelemetry import trace

from risk_gates.schemas import (
    GateAction,
    PostLLMDecision,
    PostLLMRequest,
)
from risk_gates.evaluator import evaluate_post_llm

tracer = trace.get_tracer("staq.risk_gates.gates.post_llm")

_DISCLAIMER = (
    "\n\n---\n"
    "*Disclaimer: This information is for educational purposes only and does not "
    "constitute financial advice. Please consult a licensed financial advisor before "
    "making investment decisions.*"
)


async def run_post_llm_gate(request: PostLLMRequest) -> PostLLMDecision:
    """Full post-LLM gate: OPA evaluation + disclaimer injection when needed."""
    with tracer.start_as_current_span("gate.post_llm.run"):
        decision = await evaluate_post_llm(request)

        if decision.gate_decision.action == GateAction.MODIFY:
            modified = request.llm_response + _DISCLAIMER
            return PostLLMDecision(
                gate_decision=decision.gate_decision,
                modified_response=modified,
                compliance_flags=decision.compliance_flags,
                hallucination_markers=decision.hallucination_markers,
            )

        return decision
