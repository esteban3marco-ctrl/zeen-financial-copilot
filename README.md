# Zeen Financial Copilot

[![Tests](https://img.shields.io/badge/tests-491%20passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-purple)](https://github.com/langchain-ai/langgraph)
[![OPA](https://img.shields.io/badge/OPA-Rego%20policies-orange)](https://www.openpolicyagent.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://react.dev/)

> AI-powered Financial Copilot with 4-layer Risk Gate Framework built for the Staq Intelligence Platform

---

## Overview

Zeen is a production-ready Financial AI Copilot that combines a **LangGraph agentic runtime** with a **4-layer OPA-based Risk Gate Framework** to deliver safe, role-aware financial assistance. Every user message passes through pre-LLM and post-LLM safety checks; every tool call is guarded by pre-tool and post-tool policies — all evaluated by Open Policy Agent (OPA) Rego policies with a Python fallback for resilience.

---

## Architecture — Risk Gate Pipeline

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    GATE LAYER 1: pre_llm                    │
│  • Prompt injection detection                               │
│  • Rate limiting per role (basic=30, premium=100, adv=200)  │
│  • Input length / content policy                            │
└─────────────────────────┬───────────────────────────────────┘
                          │  ALLOW
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   LangGraph Agent Runtime                   │
│                                                             │
│   input_validator → pre_llm_gate → llm_invoke              │
│         │                               │                   │
│         └── tool_router ────────────────┘                   │
│                  │                                          │
│         ┌────────▼────────┐                                 │
│         │  GATE LAYER 2   │  pre_tool                       │
│         │  Tool whitelist │  Role-based tool authorization  │
│         │  (basic=5 tools)│  (premium=8, advisor=11)        │
│         └────────┬────────┘                                 │
│                  │  ALLOW                                   │
│         ┌────────▼────────┐                                 │
│         │  Tool Executor  │  MCP tools + E2B Sandbox        │
│         └────────┬────────┘                                 │
│         ┌────────▼────────┐                                 │
│         │  GATE LAYER 3   │  post_tool                      │
│         │  Secrets redact │  PII detection, result audit    │
│         └────────┬────────┘                                 │
│                  └──────────────────────┐                   │
│                                         ▼                   │
│                                    response_formatter       │
└─────────────────────────────────────────┬───────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   GATE LAYER 4: post_llm                    │
│  • Regulated financial advice detection (buy/sell)          │
│  • PII leakage check                                        │
│  • Disclaimer enforcement for advisor-role responses        │
└─────────────────────────┬───────────────────────────────────┘
                          │  ALLOW / DENY / MODIFY
                          ▼
                     Final Response
                  (streamed via WebSocket)
```

---

## Role Permissions

| Feature | Basic | Premium | Advisor |
|---|---|---|---|
| **Rate limit** | 30 req/window | 100 req/window | 200 req/window |
| **Available tools** | 5 | 8 | 11 |
| `market_data_lookup` | ✅ | ✅ | ✅ |
| `portfolio_summary` | ✅ | ✅ | ✅ |
| `financial_calculator` | ✅ | ✅ | ✅ |
| `news_search` | ✅ | ✅ | ✅ |
| `economic_indicators` | ✅ | ✅ | ✅ |
| `portfolio_optimizer` | ❌ | ✅ | ✅ |
| `risk_analyzer` | ❌ | ✅ | ✅ |
| `backtesting_engine` | ❌ | ✅ | ✅ |
| `trade_executor` | ❌ | ❌ | ✅ |
| `client_portfolio` | ❌ | ❌ | ✅ |
| `compliance_check` | ❌ | ❌ | ✅ |
| **Buy/sell recommendations** | ❌ blocked | ❌ blocked | ✅ with disclaimer |
| **System prompt** | General info only | Portfolio analysis | Full advice |

---

## Quick Start (3 steps)

### 1. Install dependencies

```bash
# Python backend
pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set:
# ANTHROPIC_API_KEY=sk-ant-...
# SUPABASE_URL=https://your-project.supabase.co   (optional)
# SUPABASE_SERVICE_KEY=...                         (optional)
```

### 3. Run

```bash
# Terminal 1 — Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
# Open http://localhost:5173
```

> **OPA is optional** — if not installed, the system automatically falls back to Python-based policy evaluation with identical behavior.

---

## Demo Scenarios

### Scenario 1 — Market Data Query (Basic role)
```
User: "What is the current price of AAPL?"
→ pre_llm: ALLOW (clean input, within rate limit)
→ Tool: market_data_lookup(ticker="AAPL")
→ pre_tool: ALLOW (market_data_lookup in basic whitelist)
→ post_tool: ALLOW (no secrets, no PII)
→ post_llm: ALLOW (factual data, no investment advice)
Result: Price data streamed to user
```

### Scenario 2 — Regulated Advice Block (Basic role)
```
User: "Should I buy AAPL stock right now?"
→ pre_llm: ALLOW
→ LLM generates buy recommendation
→ post_llm: DENY (regulated financial advice for non-advisor role)
Result: Request blocked, user informed of role limitation
```

### Scenario 3 — Advisor Full Access
```
User: "Analyze my portfolio and recommend rebalancing"
→ pre_llm: ALLOW (advisor, 200 req/window)
→ Tools: portfolio_summary + risk_analyzer + trade_executor
→ post_llm: ALLOW (advisor role + disclaimer auto-appended)
Result: Full investment recommendation with compliance disclaimer
```

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **AI Runtime** | LangGraph | 0.2.x |
| **LLM** | Anthropic Claude | claude-3-5-haiku |
| **Policy Engine** | Open Policy Agent (OPA) | 0.70+ |
| **Backend** | FastAPI | 0.115 |
| **Database** | Supabase (PostgreSQL) | 2.x |
| **Frontend** | React + TypeScript | 18 / 5.x |
| **State Management** | Zustand | 5.x |
| **Streaming** | WebSockets (native) | — |
| **Observability** | OpenTelemetry | 1.x |
| **Sandbox** | E2B (code execution) | 1.x |
| **Tool Protocol** | MCP (Model Context Protocol) | 1.x |
| **Schema Validation** | Pydantic v2 | 2.x |
| **Testing** | pytest + pytest-asyncio | 9.x |
| **Build** | Vite | 6.x |
| **Language** | Python 3.12 + TypeScript | — |

---

## Project Structure

```
staq-zeen/
├── agent_runtime/          # LangGraph graph + 10 nodes
│   ├── graph.py            # StateGraph with conditional edges
│   ├── state.py            # AgentState (Pydantic v2)
│   └── nodes/              # input_validator, llm_invoke, tool_executor, ...
├── risk_gates/             # 4-layer OPA Risk Gate Framework
│   ├── evaluator.py        # OPA HTTP client + Python fallback
│   ├── gates/              # pre_llm, post_llm, pre_tool, post_tool
│   ├── opa/                # Rego policies (.rego files)
│   └── schemas.py          # GateDecision, RiskContext, UserRole
├── tools/                  # MCP tool registry + E2B sandbox
├── memory/                 # Supabase conversation + session + checkpointer
├── backend/                # FastAPI application
│   ├── routers/            # /api/chat, /api/sessions, /api/health, /api/demo
│   ├── websocket/          # WS handler + streaming adapter
│   └── services/           # AgentService, ScenarioService
├── frontend/               # React + TypeScript SPA
│   ├── src/components/     # Chat, RiskPanel, ToolPanel, MemoryPanel
│   ├── src/hooks/          # useChat, useWebSocket, useAuth
│   └── src/store/          # Zustand stores (chat, gate, tool, session)
├── migrations/             # 6 Supabase SQL migrations with RLS
└── tests/                  # 491 tests, 94% coverage
```

---

## Running Tests

```bash
# Full suite with coverage
pytest --cov=. --cov-report=term-missing -q

# Specific module
pytest tests/risk_gates/ -v
pytest tests/agent_runtime/ -v

# Type checking
mypy . --ignore-missing-imports
```

---

## Key Design Decisions

- **Fail-safe gates**: OPA unavailability triggers Python fallback — the system never fails open or closed unexpectedly
- **Streaming-first**: WebSocket streaming with `asyncio.create_task` for parallel gate evaluation during LLM streaming
- **Role-aware prompts**: Each user role gets a distinct system prompt, not just policy enforcement
- **E2B isolation**: Financial calculations run in isolated E2B sandboxes to prevent code injection
- **OTel tracing**: Every gate evaluation, LLM call, and tool execution emits OpenTelemetry spans

---

> Built as a technical demonstration for the **Staq Zeen Intelligence Platform**
