"""Tests for settings router endpoints."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from models import ActivityLog


class TestAutoEditSettings:
    """Test GET/PUT /settings/auto-edit endpoints."""

    def test_get_auto_edit_settings(self, client: TestClient, db_session):
        """GET /settings/auto-edit returns current config values."""
        response = client.get("/settings/auto-edit")
        assert response.status_code == 200
        data = response.json()

        # Should contain all expected keys
        assert "enabled" in data
        assert "threshold" in data
        assert "max_cost_per_storyboard" in data
        assert "max_retries_per_scene" in data

        # Types
        assert isinstance(data["enabled"], bool)
        assert isinstance(data["threshold"], (int, float))
        assert isinstance(data["max_cost_per_storyboard"], (int, float))
        assert isinstance(data["max_retries_per_scene"], int)

    def test_update_auto_edit_settings(self, client: TestClient, db_session):
        """PUT /settings/auto-edit updates runtime config."""
        update_data = {
            "enabled": True,
            "threshold": 0.85,
            "max_cost": 2.5,
            "max_retries": 3,
        }

        response = client.put("/settings/auto-edit", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "current" in data
        assert data["current"]["enabled"] is True
        assert data["current"]["threshold"] == 0.85
        assert data["current"]["max_cost"] == 2.5
        assert data["current"]["max_retries"] == 3

    def test_update_modifies_config_module(self, client: TestClient, db_session):
        """PUT updates the config module attributes at runtime.

        Note: The GET handler uses `from config import X` which creates
        local name bindings at import time. The PUT handler writes to
        `config.X` via `import config`. The config module attributes
        are updated, which we verify directly.
        """
        import config

        # Save original values to restore after test
        orig_enabled = config.GEMINI_AUTO_EDIT_ENABLED
        orig_threshold = config.GEMINI_AUTO_EDIT_THRESHOLD
        orig_cost = config.GEMINI_AUTO_EDIT_MAX_COST_PER_STORYBOARD
        orig_retries = config.GEMINI_AUTO_EDIT_MAX_RETRIES_PER_SCENE

        try:
            update_data = {
                "enabled": True,
                "threshold": 0.9,
                "max_cost": 5.0,
                "max_retries": 5,
            }
            put_resp = client.put("/settings/auto-edit", json=update_data)
            assert put_resp.status_code == 200

            # Verify config module was updated
            assert config.GEMINI_AUTO_EDIT_ENABLED is True
            assert config.GEMINI_AUTO_EDIT_THRESHOLD == 0.9
            assert config.GEMINI_AUTO_EDIT_MAX_COST_PER_STORYBOARD == 5.0
            assert config.GEMINI_AUTO_EDIT_MAX_RETRIES_PER_SCENE == 5
        finally:
            # Restore original config to avoid polluting other tests
            config.GEMINI_AUTO_EDIT_ENABLED = orig_enabled
            config.GEMINI_AUTO_EDIT_THRESHOLD = orig_threshold
            config.GEMINI_AUTO_EDIT_MAX_COST_PER_STORYBOARD = orig_cost
            config.GEMINI_AUTO_EDIT_MAX_RETRIES_PER_SCENE = orig_retries

    def test_update_auto_edit_missing_fields(self, client: TestClient, db_session):
        """PUT with missing required fields returns 422."""
        # Missing max_retries
        incomplete = {
            "enabled": True,
            "threshold": 0.8,
            "max_cost": 1.0,
        }
        response = client.put("/settings/auto-edit", json=incomplete)
        assert response.status_code == 422

    def test_update_auto_edit_invalid_types(self, client: TestClient, db_session):
        """PUT with wrong types returns 422."""
        invalid = {
            "enabled": "not_a_bool",
            "threshold": "not_a_float",
            "max_cost": "not_a_float",
            "max_retries": "not_an_int",
        }
        response = client.put("/settings/auto-edit", json=invalid)
        assert response.status_code == 422


class TestCostSummary:
    """Test GET /settings/auto-edit/cost-summary endpoint."""

    def test_cost_summary_empty(self, client: TestClient, db_session):
        """Cost summary with no activity logs returns zeros."""
        response = client.get("/settings/auto-edit/cost-summary")
        assert response.status_code == 200
        data = response.json()

        assert data["today"] == 0.0
        assert data["this_week"] == 0.0
        assert data["this_month"] == 0.0
        assert data["total"] == 0.0
        assert data["edit_count_today"] == 0
        assert data["edit_count_month"] == 0

    def test_cost_summary_with_data(self, client: TestClient, db_session):
        """Cost summary with activity logs returns correct aggregations."""
        now = datetime.now()

        # Create activity logs with gemini edits
        log1 = ActivityLog(
            prompt="test prompt 1",
            gemini_edited=True,
            gemini_cost_usd=0.05,
            created_at=now,
        )
        log2 = ActivityLog(
            prompt="test prompt 2",
            gemini_edited=True,
            gemini_cost_usd=0.10,
            created_at=now,
        )
        # Non-edited log should not count
        log3 = ActivityLog(
            prompt="test prompt 3",
            gemini_edited=False,
            gemini_cost_usd=0.0,
            created_at=now,
        )
        db_session.add_all([log1, log2, log3])
        db_session.commit()

        response = client.get("/settings/auto-edit/cost-summary")
        assert response.status_code == 200
        data = response.json()

        assert data["today"] == 0.15
        assert data["edit_count_today"] == 2
        assert data["total"] == 0.15

    def test_cost_summary_old_data_excluded_from_today(
        self, client: TestClient, db_session
    ):
        """Old activity logs excluded from today count but included in total."""
        now = datetime.now()
        yesterday = now - timedelta(days=2)

        log_today = ActivityLog(
            prompt="today prompt",
            gemini_edited=True,
            gemini_cost_usd=0.05,
            created_at=now,
        )
        log_old = ActivityLog(
            prompt="old prompt",
            gemini_edited=True,
            gemini_cost_usd=0.20,
            created_at=yesterday,
        )
        db_session.add_all([log_today, log_old])
        db_session.commit()

        response = client.get("/settings/auto-edit/cost-summary")
        assert response.status_code == 200
        data = response.json()

        assert data["today"] == 0.05
        assert data["edit_count_today"] == 1
        assert data["total"] == 0.25
