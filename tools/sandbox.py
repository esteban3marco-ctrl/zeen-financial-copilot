"""E2B sandbox wrapper: execute code in isolated sandboxes."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import TYPE_CHECKING, Any, Literal

from tools.schemas import SANDBOX_LIMITS_BY_ROLE, SandboxRequest, SandboxResult

logger = logging.getLogger(__name__)

# Module-level import so tests can patch tools.sandbox.AsyncSandbox
try:
    from e2b_code_interpreter import AsyncSandbox
except ImportError:
    AsyncSandbox = None

_VALID_LANGUAGES: frozenset[str] = frozenset({"python", "javascript", "shell"})


async def run_in_sandbox(
    call_id: str,
    tool_name: str,
    code: str,
    language: str = "python",
    user_role: str = "basic",
) -> SandboxResult:
    """Execute code in an E2B sandbox with role-based resource limits."""
    limits = SANDBOX_LIMITS_BY_ROLE.get(user_role, SANDBOX_LIMITS_BY_ROLE["basic"])
    safe_lang: Literal["python", "javascript", "shell"] = (
        language if language in _VALID_LANGUAGES else "python"  # type: ignore[assignment]
    )
    request = SandboxRequest(
        call_id=call_id,
        tool_name=tool_name,
        code=code,
        language=safe_lang,
        resource_limits=limits,
    )
    return await _execute_sandbox(request)


async def _execute_sandbox(request: SandboxRequest) -> SandboxResult:
    """Create E2B sandbox, run code, return result."""
    api_key = os.getenv("E2B_API_KEY")
    if not api_key:
        logger.error("E2B_API_KEY not set — cannot create sandbox")
        return SandboxResult(
            call_id=request.call_id,
            status="error",
            stderr="E2B_API_KEY not configured",
            exit_code=1,
        )

    if AsyncSandbox is None:
        return SandboxResult(
            call_id=request.call_id,
            status="error",
            stderr="e2b_code_interpreter package not installed",
            exit_code=1,
        )

    start_ms = time.monotonic() * 1000
    timeout_s = request.resource_limits.timeout_ms / 1000.0

    try:
        async with AsyncSandbox(api_key=api_key) as sandbox:
            execution = await asyncio.wait_for(
                sandbox.run_code(request.code, language=request.language),
                timeout=timeout_s,
            )

            elapsed = time.monotonic() * 1000 - start_ms
            stdout = "\n".join(str(r) for r in execution.results or [])
            stderr = "\n".join(execution.error.traceback if execution.error else [])
            exit_code = 1 if execution.error else 0

            final_status: Literal["success", "error"]
            if len(stdout.encode()) > request.resource_limits.max_output_bytes:
                final_status = "error"
                stderr = "Output exceeds maximum allowed size"
                exit_code = 1
            else:
                final_status = "success" if exit_code == 0 else "error"

            return SandboxResult(
                call_id=request.call_id,
                status=final_status,
                stdout=stdout[:request.resource_limits.max_output_bytes],
                stderr=stderr,
                exit_code=exit_code,
                execution_time_ms=elapsed,
            )

    except asyncio.TimeoutError:
        return SandboxResult(
            call_id=request.call_id,
            status="timeout",
            stderr=f"Sandbox execution timed out after {request.resource_limits.timeout_ms}ms",
            exit_code=124,
            execution_time_ms=request.resource_limits.timeout_ms,
        )
    except Exception as exc:
        logger.exception("Sandbox execution failed for call_id=%s", request.call_id)
        return SandboxResult(
            call_id=request.call_id,
            status="error",
            stderr=str(exc),
            exit_code=1,
            execution_time_ms=time.monotonic() * 1000 - start_ms,
        )
