"""TDD tests for Creative Engine router endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from models.creative import CreativeAgentPreset, CreativeSession

# ── Sessions ─────────────────────────────────────────────────


class TestCreateSession:
    """POST /lab/creative/sessions"""

    def test_create_session_success(self, client: TestClient, db_session):
        """Create a new creative session."""
        session = CreativeSession(
            id=1,
            objective="Write a story",
            evaluation_criteria={"originality": {"weight": 0.5}},
            max_rounds=3,
            status="running",
        )
        with patch(
            "routers.creative.create_session",
            new_callable=AsyncMock,
            return_value=session,
        ):
            resp = client.post(
                "/lab/creative/sessions",
                json={"objective": "Write a story"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["objective"] == "Write a story"
        assert data["status"] == "running"

    def test_create_session_missing_objective(self, client: TestClient):
        """Missing objective should fail validation."""
        resp = client.post("/lab/creative/sessions", json={})
        assert resp.status_code == 422


class TestListSessions:
    """GET /lab/creative/sessions"""

    def test_list_sessions_empty(self, client: TestClient):
        """Empty DB returns zero items."""
        resp = client.get("/lab/creative/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_sessions_with_data(self, client: TestClient, db_session):
        """List returns existing sessions."""
        session = CreativeSession(
            objective="Test",
            evaluation_criteria={},
            max_rounds=3,
            status="running",
        )
        db_session.add(session)
        db_session.commit()

        resp = client.get("/lab/creative/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["objective"] == "Test"

    def test_list_sessions_excludes_deleted(
        self,
        client: TestClient,
        db_session,
    ):
        """Soft-deleted sessions are excluded."""
        session = CreativeSession(
            objective="Deleted",
            evaluation_criteria={},
            max_rounds=3,
            status="running",
            deleted_at=datetime.now(UTC),
        )
        db_session.add(session)
        db_session.commit()

        resp = client.get("/lab/creative/sessions")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestGetSession:
    """GET /lab/creative/sessions/{id}"""

    def test_get_session_by_id(self, client: TestClient, db_session):
        """Retrieve session by ID."""
        session = CreativeSession(
            objective="Get me",
            evaluation_criteria={},
            max_rounds=3,
            status="running",
        )
        db_session.add(session)
        db_session.commit()

        resp = client.get(f"/lab/creative/sessions/{session.id}")
        assert resp.status_code == 200
        assert resp.json()["objective"] == "Get me"

    def test_get_session_not_found(self, client: TestClient):
        """Non-existent ID returns 404."""
        resp = client.get("/lab/creative/sessions/99999")
        assert resp.status_code == 404

    def test_get_deleted_session_returns_404(
        self,
        client: TestClient,
        db_session,
    ):
        """Soft-deleted session returns 404."""
        session = CreativeSession(
            objective="Deleted",
            evaluation_criteria={},
            max_rounds=3,
            status="running",
            deleted_at=datetime.now(UTC),
        )
        db_session.add(session)
        db_session.commit()

        resp = client.get(f"/lab/creative/sessions/{session.id}")
        assert resp.status_code == 404


class TestDeleteSession:
    """DELETE /lab/creative/sessions/{id}"""

    def test_delete_session(self, client: TestClient, db_session):
        """Soft-delete sets deleted_at."""
        session = CreativeSession(
            objective="Delete me",
            evaluation_criteria={},
            max_rounds=3,
            status="running",
        )
        db_session.add(session)
        db_session.commit()
        sid = session.id

        resp = client.delete(f"/lab/creative/sessions/{sid}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify soft-deleted
        db_session.expire_all()
        s = db_session.get(CreativeSession, sid)
        assert s.deleted_at is not None

    def test_delete_session_not_found(self, client: TestClient):
        """Delete non-existent session returns 404."""
        resp = client.delete("/lab/creative/sessions/99999")
        assert resp.status_code == 404


# ── Agent Presets ────────────────────────────────────────────


class TestListPresets:
    """GET /lab/creative/agent-presets"""

    def test_list_presets_empty(self, client: TestClient):
        """Empty DB returns empty list."""
        resp = client.get("/lab/creative/agent-presets")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_presets_excludes_deleted(
        self,
        client: TestClient,
        db_session,
    ):
        """Soft-deleted presets are excluded."""
        preset = CreativeAgentPreset(
            name="Deleted",
            role_description="test",
            system_prompt="test",
            model_provider="gemini",
            model_name="gemini-2.0-flash",
            deleted_at=datetime.now(UTC),
        )
        db_session.add(preset)
        db_session.commit()

        resp = client.get("/lab/creative/agent-presets")
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreatePreset:
    """POST /lab/creative/agent-presets"""

    def test_create_preset(self, client: TestClient, db_session):
        """Create a new agent preset."""
        resp = client.post(
            "/lab/creative/agent-presets",
            json={
                "name": "Test Agent",
                "role_description": "A test agent",
                "system_prompt": "You are a test agent.",
                "model_provider": "gemini",
                "model_name": "gemini-2.0-flash",
                "temperature": 0.7,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Agent"
        assert data["model_provider"] == "gemini"
        assert data["is_system"] is False


class TestUpdatePreset:
    """PUT /lab/creative/agent-presets/{id}"""

    def test_update_preset(self, client: TestClient, db_session):
        """Update a user-created preset."""
        preset = CreativeAgentPreset(
            name="Original",
            role_description="test",
            system_prompt="test",
            model_provider="gemini",
            model_name="gemini-2.0-flash",
            is_system=False,
        )
        db_session.add(preset)
        db_session.commit()

        resp = client.put(
            f"/lab/creative/agent-presets/{preset.id}",
            json={"name": "Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_update_system_preset_allowed(
        self,
        client: TestClient,
        db_session,
    ):
        """System presets can be edited (e.g. temperature, system_prompt)."""
        preset = CreativeAgentPreset(
            name="System",
            role_description="test",
            system_prompt="test",
            model_provider="gemini",
            model_name="gemini-2.0-flash",
            is_system=True,
        )
        db_session.add(preset)
        db_session.commit()

        resp = client.put(
            f"/lab/creative/agent-presets/{preset.id}",
            json={"temperature": 0.5},
        )
        assert resp.status_code == 200
        assert resp.json()["temperature"] == 0.5

    def test_update_preset_not_found(self, client: TestClient):
        """Update non-existent preset returns 404."""
        resp = client.put(
            "/lab/creative/agent-presets/99999",
            json={"name": "X"},
        )
        assert resp.status_code == 404


class TestDeletePreset:
    """DELETE /lab/creative/agent-presets/{id}"""

    def test_delete_preset(self, client: TestClient, db_session):
        """Soft-delete a user-created preset."""
        preset = CreativeAgentPreset(
            name="Delete me",
            role_description="test",
            system_prompt="test",
            model_provider="gemini",
            model_name="gemini-2.0-flash",
            is_system=False,
        )
        db_session.add(preset)
        db_session.commit()

        resp = client.delete(f"/lab/creative/agent-presets/{preset.id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_delete_system_preset_blocked(
        self,
        client: TestClient,
        db_session,
    ):
        """System presets cannot be deleted."""
        preset = CreativeAgentPreset(
            name="System",
            role_description="test",
            system_prompt="test",
            model_provider="gemini",
            model_name="gemini-2.0-flash",
            is_system=True,
        )
        db_session.add(preset)
        db_session.commit()

        resp = client.delete(f"/lab/creative/agent-presets/{preset.id}")
        assert resp.status_code == 400

    def test_delete_preset_not_found(self, client: TestClient):
        """Delete non-existent preset returns 404."""
        resp = client.delete("/lab/creative/agent-presets/99999")
        assert resp.status_code == 404
