"""
Tests for backend HTTP routers using FastAPI TestClient.

Covers:
- health.py (GET /health, GET /health/ready)
- demo.py   (GET /demo/scenarios, POST /demo/scenario)
- chat.py   (POST /chat)
- sessions.py (GET /sessions, DELETE /sessions/{id})
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.schemas.chat import ChatResponse, MessageOut, TurnMetadataOut

# ---------------------------------------------------------------------------
# Shared mock ChatResponse
# ---------------------------------------------------------------------------

_MOCK_CHAT_RESPONSE = ChatResponse(
    session_id="test-session",
    request_id="test-req",
    message=MessageOut(
        role="ai",
        content="Hello!",
        turn_index=1,
        created_at=datetime.now(timezone.utc),
    ),
    gate_events=[],
    tool_events=[],
    metadata=TurnMetadataOut(
        trace_id="t1",
        model_used="claude",
        tokens_prompt=10,
        tokens_completion=20,
        latency_ms=100.0,
        iteration_count=1,
    ),
    blocked=False,
)


# ---------------------------------------------------------------------------
# App + client fixture using dependency_overrides
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app_and_mock():
    """Create app with agent service mocked via dependency_overrides."""
    from backend.config import get_settings
    get_settings.cache_clear()

    from backend.main import create_app
    from backend.dependencies import get_agent_service

    mock_agent_svc = MagicMock()
    mock_agent_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)

    app = create_app()
    app.dependency_overrides[get_agent_service] = lambda: mock_agent_svc

    return app, mock_agent_svc


@pytest.fixture(scope="module")
def client(app_and_mock):
    app, mock_svc = app_and_mock
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, mock_svc


# ---------------------------------------------------------------------------
# Health router tests
# ---------------------------------------------------------------------------

class TestHealthRouter:
    def test_health_returns_200(self, client):
        c, _ = client
        resp = c.get("/api/health")
        assert resp.status_code == 200

    def test_health_response_has_status(self, client):
        c, _ = client
        resp = c.get("/api/health")
        data = resp.json()
        assert "status" in data
        assert data["status"] == "ok"

    def test_health_response_has_demo_mode(self, client):
        c, _ = client
        resp = c.get("/api/health")
        data = resp.json()
        assert "demo_mode" in data

    def test_health_response_has_uptime(self, client):
        c, _ = client
        resp = c.get("/api/health")
        data = resp.json()
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))

    def test_health_ready_returns_200(self, client):
        """Readiness endpoint always returns HTTP 200 (ready flag may be false)."""
        c, _ = client
        resp = c.get("/api/health/ready")
        assert resp.status_code == 200

    def test_health_ready_has_ready_flag(self, client):
        c, _ = client
        resp = c.get("/api/health/ready")
        data = resp.json()
        assert "ready" in data
        assert isinstance(data["ready"], bool)

    def test_health_ready_has_checks(self, client):
        c, _ = client
        resp = c.get("/api/health/ready")
        data = resp.json()
        assert "checks" in data
        assert isinstance(data["checks"], dict)

    def test_health_ready_checks_supabase(self, client):
        c, _ = client
        resp = c.get("/api/health/ready")
        data = resp.json()
        assert "supabase" in data["checks"]

    def test_health_ready_checks_opa(self, client):
        c, _ = client
        resp = c.get("/api/health/ready")
        data = resp.json()
        assert "opa" in data["checks"]


# ---------------------------------------------------------------------------
# Demo router tests
# ---------------------------------------------------------------------------

class TestDemoRouter:
    def test_list_scenarios_returns_200(self, client):
        c, _ = client
        resp = c.get("/api/demo/scenarios")
        assert resp.status_code == 200

    def test_list_scenarios_returns_list(self, client):
        c, _ = client
        resp = c.get("/api/demo/scenarios")
        data = resp.json()
        assert "scenarios" in data
        assert isinstance(data["scenarios"], list)

    def test_list_scenarios_has_three_items(self, client):
        c, _ = client
        resp = c.get("/api/demo/scenarios")
        data = resp.json()
        assert len(data["scenarios"]) == 3

    def test_list_scenarios_item_has_expected_keys(self, client):
        c, _ = client
        resp = c.get("/api/demo/scenarios")
        scenarios = resp.json()["scenarios"]
        for s in scenarios:
            assert "scenario_id" in s
            assert "description" in s
            assert "risk_level" in s
            assert "role" in s

    def test_run_scenario_safe_portfolio(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post("/api/demo/scenario", json={"scenario_id": "safe_portfolio"})
        assert resp.status_code == 200

    def test_run_scenario_response_structure(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post("/api/demo/scenario", json={"scenario_id": "safe_portfolio"})
        data = resp.json()
        assert "session_id" in data
        assert "injected_message" in data
        assert "expected_behavior" in data
        assert "risk_level" in data
        assert "chat_response" in data

    def test_run_scenario_not_found_returns_404(self, client):
        c, _ = client
        resp = c.post("/api/demo/scenario", json={"scenario_id": "nonexistent_scenario"})
        assert resp.status_code == 404

    def test_run_scenario_high_risk(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post("/api/demo/scenario", json={"scenario_id": "high_risk_blocked"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_level"] == "high"

    def test_run_scenario_moderate_trading(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post("/api/demo/scenario", json={"scenario_id": "moderate_trading"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_level"] == "medium"

    def test_run_scenario_with_session_id(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post(
            "/api/demo/scenario",
            json={"scenario_id": "safe_portfolio", "session_id": "my-session-123"},
        )
        assert resp.status_code == 200

    def test_run_scenario_chat_response_embedded(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post("/api/demo/scenario", json={"scenario_id": "safe_portfolio"})
        data = resp.json()
        chat_resp = data["chat_response"]
        assert "message" in chat_resp
        assert "session_id" in chat_resp


# ---------------------------------------------------------------------------
# Chat router tests (DEMO_MODE — no auth token required)
# ---------------------------------------------------------------------------

class TestChatRouter:
    def test_chat_returns_200(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post("/api/chat", json={"message": "hello"})
        assert resp.status_code == 200

    def test_chat_response_has_session_id(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post("/api/chat", json={"message": "hello"})
        data = resp.json()
        assert "session_id" in data

    def test_chat_response_has_message(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post("/api/chat", json={"message": "hello"})
        data = resp.json()
        assert "message" in data
        assert "content" in data["message"]

    def test_chat_with_explicit_session_id(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post("/api/chat", json={"message": "hello", "session_id": "sess-abc"})
        assert resp.status_code == 200

    def test_chat_empty_message_rejected(self, client):
        """Pydantic min_length=1 constraint rejects empty messages."""
        c, _ = client
        resp = c.post("/api/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_chat_response_has_blocked_field(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post("/api/chat", json={"message": "hello"})
        data = resp.json()
        assert "blocked" in data
        assert data["blocked"] is False

    def test_chat_response_has_metadata(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post("/api/chat", json={"message": "hello"})
        data = resp.json()
        assert "metadata" in data
        assert "model_used" in data["metadata"]

    def test_chat_response_has_gate_and_tool_events(self, client):
        c, mock_svc = client
        mock_svc.run_turn = AsyncMock(return_value=_MOCK_CHAT_RESPONSE)
        resp = c.post("/api/chat", json={"message": "hello"})
        data = resp.json()
        assert "gate_events" in data
        assert "tool_events" in data

    def test_chat_missing_message_field_rejected(self, client):
        c, _ = client
        resp = c.post("/api/chat", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Sessions router tests
# ---------------------------------------------------------------------------

class TestSessionsRouter:
    def test_list_sessions_returns_200_no_supabase(self, client):
        """Without Supabase env vars, list returns 200 with empty list."""
        c, _ = client
        resp = c.get("/api/sessions")
        assert resp.status_code == 200

    def test_list_sessions_returns_list(self, client):
        c, _ = client
        resp = c.get("/api/sessions")
        data = resp.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_list_sessions_has_total(self, client):
        c, _ = client
        resp = c.get("/api/sessions")
        data = resp.json()
        assert "total" in data
        assert isinstance(data["total"], int)

    def test_delete_session_no_supabase_returns_503(self, client):
        """Without Supabase env vars, delete returns 503."""
        c, _ = client
        resp = c.delete("/api/sessions/some-session-id")
        assert resp.status_code == 503

    def test_get_session_no_supabase_returns_503(self, client):
        """Without Supabase env vars, get single session returns 503."""
        c, _ = client
        resp = c.get("/api/sessions/some-session-id")
        assert resp.status_code == 503

    def test_delete_session_with_mocked_supabase(self, client):
        """Delete returns 204 when Supabase is mocked and row is found."""
        c, _ = client

        mock_result = MagicMock()
        mock_result.data = [{"session_id": "test-sess", "user_id": "demo-user"}]

        mock_table = MagicMock()
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = mock_result

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        # create_client is imported locally inside the router function body,
        # so we patch the supabase module directly.
        with patch("supabase.create_client", return_value=mock_supabase):
            with patch.dict(
                "os.environ",
                {"SUPABASE_URL": "http://fake", "SUPABASE_SERVICE_KEY": "fakekey"},
            ):
                resp = c.delete("/api/sessions/test-sess")
        assert resp.status_code == 204

    def test_list_sessions_with_mocked_supabase(self, client):
        """list_sessions returns sessions when Supabase is mocked."""
        c, _ = client

        mock_result = MagicMock()
        mock_result.data = [
            {
                "session_id": "sess-001",
                "user_id": "demo-user",
                "turn_count": 2,
                "total_tokens": 150,
                "status": "active",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T01:00:00Z",
            }
        ]

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = mock_result

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        with patch("supabase.create_client", return_value=mock_supabase):
            with patch.dict(
                "os.environ",
                {"SUPABASE_URL": "http://fake", "SUPABASE_SERVICE_KEY": "fakekey"},
            ):
                resp = c.get("/api/sessions")

        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data
        assert "total" in data


# ---------------------------------------------------------------------------
# Root endpoint sanity check
# ---------------------------------------------------------------------------

class TestRootEndpoint:
    def test_root_returns_200(self, client):
        c, _ = client
        resp = c.get("/")
        assert resp.status_code == 200

    def test_root_has_service_name(self, client):
        c, _ = client
        resp = c.get("/")
        data = resp.json()
        assert data.get("service") == "staq-zeen-backend"

    def test_root_has_version(self, client):
        c, _ = client
        resp = c.get("/")
        data = resp.json()
        assert "version" in data
