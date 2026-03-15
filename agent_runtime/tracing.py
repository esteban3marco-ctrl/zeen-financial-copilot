"""OpenTelemetry setup and span attribute constants for the agent runtime."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode

# Module-level tracer — configured once at startup via setup_tracing()
_tracer: trace.Tracer = trace.get_tracer("staq.agent_runtime")


def setup_tracing(endpoint: str | None = None) -> None:
    """Configure OTel tracer provider. Call once at application startup."""
    provider = TracerProvider()
    if endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    global _tracer
    _tracer = trace.get_tracer("staq.agent_runtime")


def get_tracer() -> trace.Tracer:
    return _tracer


# ── Span attribute constants ──────────────────────────────────────────────

class Attrs:
    """Standard span attribute keys."""
    REQUEST_ID = "staq.request_id"
    SESSION_ID = "staq.session_id"
    USER_ID = "staq.user_id"
    USER_ROLE = "staq.user_role"
    TRACE_ID = "staq.trace_id"

    # Node attrs
    NODE_NAME = "staq.node.name"
    NEXT_ACTION = "staq.node.next_action"
    INPUT_LENGTH = "staq.node.input_length"

    # Gate attrs
    GATE_NAME = "staq.gate.name"
    GATE_ACTION = "staq.gate.action"
    GATE_REASON = "staq.gate.reason"
    INJECTION_SCORE = "staq.gate.injection_score"
    PII_COUNT = "staq.gate.pii_count"
    COMPLIANCE_FLAGS = "staq.gate.compliance_flags"

    # LLM attrs
    LLM_MODEL = "staq.llm.model"
    LLM_TOKENS_PROMPT = "staq.llm.tokens_prompt"
    LLM_TOKENS_COMPLETION = "staq.llm.tokens_completion"
    LLM_FINISH_REASON = "staq.llm.finish_reason"
    LLM_TOOL_COUNT = "staq.llm.tool_call_count"

    # Tool attrs
    TOOL_NAME = "staq.tool.name"
    TOOL_SERVER = "staq.tool.server_id"
    TOOL_SANDBOX = "staq.tool.sandbox_used"
    TOOL_TIMEOUT_MS = "staq.tool.timeout_ms"
    TOOL_STATUS = "staq.tool.status"
    TOOL_LATENCY_MS = "staq.tool.latency_ms"
    TOOL_ITERATION = "staq.tool.iteration"

    # Error attrs
    ERROR_CODE = "staq.error.code"
    ERROR_NODE = "staq.error.node"
    ERROR_SEVERITY = "staq.error.severity"

    # Memory attrs
    MEMORY_MESSAGES_PERSISTED = "staq.memory.messages_persisted"
    MEMORY_TOKENS_TOTAL = "staq.memory.tokens_total"


@contextmanager
def agent_span(name: str, **attrs: Any) -> Generator[Span, None, None]:
    """Context manager that creates a span with staq attributes."""
    with _tracer.start_as_current_span(name) as span:
        for key, value in attrs.items():
            span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


def record_error(span: Span, code: str, message: str, node: str) -> None:
    span.set_status(Status(StatusCode.ERROR, message))
    span.set_attribute(Attrs.ERROR_CODE, code)
    span.set_attribute(Attrs.ERROR_NODE, node)
