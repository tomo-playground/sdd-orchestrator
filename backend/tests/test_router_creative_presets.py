"""Creative Agent Presets 라우터 테스트."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from models.creative import CreativeAgentPreset


class TestCreativePresetsRouter:
    """Creative Presets CRUD 엔드포인트 테스트."""

    def test_list_presets_empty(self, client: TestClient, db_session):
        response = client.get("/api/admin/lab/creative/agent-presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert "categories" in data
        assert isinstance(data["presets"], list)

    def test_create_preset(self, client: TestClient, db_session):
        req = {
            "name": "Test Preset",
            "agent_role": "test_role",
            "category": "writer",
            "role_description": "Test description",
            "system_prompt": "You are a test agent.",
        }
        response = client.post("/api/admin/lab/creative/agent-presets", json=req)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Preset"
        assert data["agent_role"] == "test_role"

    def test_list_presets_with_data(self, client: TestClient, db_session):
        preset = CreativeAgentPreset(
            name="Listed Preset",
            agent_role="listed_role",
            category="writer",
            role_description="desc",
            system_prompt="prompt",
            model_provider="gemini",
            model_name="gemini-2.5-flash",
        )
        db_session.add(preset)
        db_session.commit()

        response = client.get("/api/admin/lab/creative/agent-presets")
        assert response.status_code == 200
        data = response.json()
        assert len(data["presets"]) >= 1
        names = [p["name"] for p in data["presets"]]
        assert "Listed Preset" in names

    def test_list_presets_filter_by_category(self, client: TestClient, db_session):
        p1 = CreativeAgentPreset(name="W1", agent_role="w1", category="writer", role_description="d", system_prompt="p", model_provider="gemini", model_name="gemini-2.5-flash")
        p2 = CreativeAgentPreset(name="C1", agent_role="c1", category="critic", role_description="d", system_prompt="p", model_provider="gemini", model_name="gemini-2.5-flash")
        db_session.add_all([p1, p2])
        db_session.commit()

        response = client.get("/api/admin/lab/creative/agent-presets?category=writer")
        assert response.status_code == 200
        data = response.json()
        categories = {p["category"] for p in data["presets"]}
        assert categories == {"writer"}

    def test_update_preset(self, client: TestClient, db_session):
        preset = CreativeAgentPreset(
            name="Update Me",
            agent_role="update_role",
            category="writer",
            role_description="desc",
            system_prompt="old prompt",
            model_provider="gemini",
            model_name="gemini-2.5-flash",
        )
        db_session.add(preset)
        db_session.commit()
        pid = preset.id

        response = client.put(
            f"/api/admin/lab/creative/agent-presets/{pid}",
            json={"system_prompt": "new prompt"},
        )
        assert response.status_code == 200
        assert response.json()["system_prompt"] == "new prompt"

    def test_update_preset_not_found(self, client: TestClient, db_session):
        response = client.put(
            "/api/admin/lab/creative/agent-presets/99999",
            json={"system_prompt": "x"},
        )
        assert response.status_code == 404

    def test_delete_preset(self, client: TestClient, db_session):
        preset = CreativeAgentPreset(
            name="Delete Me",
            agent_role="del_role",
            category="writer",
            role_description="d",
            system_prompt="p",
            model_provider="gemini",
            model_name="gemini-2.5-flash",
        )
        db_session.add(preset)
        db_session.commit()
        pid = preset.id

        response = client.delete(f"/api/admin/lab/creative/agent-presets/{pid}")
        assert response.status_code == 200
        assert response.json()["ok"] is True

        # Verify soft-deleted
        db_session.expire_all()
        deleted = db_session.get(CreativeAgentPreset, pid)
        assert deleted.deleted_at is not None

    def test_delete_preset_not_found(self, client: TestClient, db_session):
        response = client.delete("/api/admin/lab/creative/agent-presets/99999")
        assert response.status_code == 404

    def test_delete_system_preset_blocked(self, client: TestClient, db_session):
        preset = CreativeAgentPreset(
            name="System Preset",
            agent_role="sys_role",
            category="writer",
            role_description="d",
            system_prompt="p",
            model_provider="gemini",
            model_name="gemini-2.5-flash",
            is_system=True,
        )
        db_session.add(preset)
        db_session.commit()
        pid = preset.id

        response = client.delete(f"/api/admin/lab/creative/agent-presets/{pid}")
        assert response.status_code == 400
        assert "system" in response.json()["detail"].lower()
