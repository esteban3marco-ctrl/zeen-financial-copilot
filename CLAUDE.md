# Staq/Zeen — Claude Instructions

## Stack
Python 3.12, LangGraph, Pydantic v2, OPA/Rego, E2B, MCP, Supabase, FastAPI, React+TypeScript, OpenTelemetry

## Structure
```
agent_runtime/   risk_gates/   tools/   memory/
recommendations/ tests/        frontend/
```

## Model Rules
- **Opus**: arquitectura, diseño, decisiones críticas, Agent Cards, políticas OPA
- **Sonnet**: TODO lo demás (implementación, refactor, debug, docs)
- Tras cada tarea de arquitectura → ejecuta `/model sonnet` antes de implementar

## Token Management
- Este archivo: máximo 60 líneas
- `/compact` al 70% de contexto de sesión
- Nueva sesión entre módulos principales
- No usar `ultrathink`
- Máximo 3 subagentes en paralelo con Task tool + Sonnet (no Agent Teams)

## Auto-Resume
Si arrancas con `claude -c` o no hay tarea activa:
1. Lee `PROGRESS.md`
2. Identifica el último módulo en progreso
3. Continúa sin preguntar
4. Actualiza `PROGRESS.md` al terminar cada subtarea

## Priority Order
1. Risk Gate Framework (OPA 4 capas)
2. LangGraph Agent Runtime
3. Financial Copilot demo
4. Tests

## Agents
- `.claude/agents/architect.md` → Opus, solo lectura, diseño
- `.claude/agents/builder.md` → Sonnet, implementación
- `.claude/agents/tester.md` → Haiku, pytest + mypy
