"""MCP and E2B tool schemas."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MCPToolParam(BaseModel):
    name: str
    type: str
    description: str = ""
    required: bool = False


class MCPToolSchema(BaseModel):
    name: str
    description: str
    server_id: str
    parameters: list[MCPToolParam] = Field(default_factory=list)
    requires_sandbox: bool = False
    timeout_ms: int = Field(default=30_000, ge=1_000, le=300_000)
    risk_level: Literal["low", "medium", "high"] = "low"


class MCPServerConfig(BaseModel):
    server_id: str
    transport: Literal["stdio", "sse", "streamable_http"]
    command: str | None = None
    url: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    timeout_ms: int = 30_000
    max_retries: int = 2


class MCPCallRequest(BaseModel):
    tool_name: str
    tool_params: dict[str, Any]
    call_id: str
    server_id: str
    timeout_ms: int = 30_000
    sanitized_params: dict[str, Any] | None = None


class MCPCallResponse(BaseModel):
    call_id: str
    tool_name: str
    success: bool
    result: Any = None
    error: str | None = None
    execution_time_ms: float = 0.0


class SandboxResourceLimits(BaseModel):
    cpu_count: int = Field(default=1, ge=1, le=4)
    memory_mb: int = Field(default=256, ge=64, le=2048)
    timeout_ms: int = Field(default=30_000, ge=5_000, le=120_000)
    max_output_bytes: int = Field(default=1_048_576)
    network_enabled: bool = False
    allowed_packages: list[str] = Field(default_factory=list)


class SandboxRequest(BaseModel):
    call_id: str
    tool_name: str
    code: str
    language: Literal["python", "javascript", "shell"] = "python"
    resource_limits: SandboxResourceLimits = Field(default_factory=SandboxResourceLimits)
    input_files: dict[str, str] = Field(default_factory=dict)
    env_vars: dict[str, str] = Field(default_factory=dict)


class SandboxResult(BaseModel):
    call_id: str
    status: Literal["success", "error", "timeout", "oom"]
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    output_files: dict[str, str] = Field(default_factory=dict)
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0


# Resource limits per user role
SANDBOX_LIMITS_BY_ROLE: dict[str, SandboxResourceLimits] = {
    "anonymous": SandboxResourceLimits(cpu_count=1, memory_mb=128, timeout_ms=10_000),
    "basic": SandboxResourceLimits(cpu_count=1, memory_mb=256, timeout_ms=30_000),
    "premium": SandboxResourceLimits(cpu_count=2, memory_mb=512, timeout_ms=60_000),
    "advisor": SandboxResourceLimits(cpu_count=2, memory_mb=1024, timeout_ms=90_000),
    "admin": SandboxResourceLimits(
        cpu_count=4, memory_mb=2048, timeout_ms=120_000, network_enabled=True
    ),
}
