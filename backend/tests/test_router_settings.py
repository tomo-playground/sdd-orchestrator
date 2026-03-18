"""Tests for settings router endpoints."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from models import ActivityLog


class TestAutoEditSettings:
    """Test GET/PUT /settings/auto-edit endpoints."""

    def test_get_auto_edit_settings(self, client: TestClient, db_session):
        """GET /settings/auto-edit returns current config values."""
        response = client.get("/api/admin/settings/auto-edit")
        assert response.status_code == 200
        data = response.json()

        # Should contain all expected keys
        assert "is_enabled" in data
        assert "threshold" in data
        assert "max_cost_per_storyboard" in data
        assert "max_retries_per_scene" in data

        # Types
        assert isinstance(data["is_enabled"], bool)
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

        response = client.put("/api/admin/settings/auto-edit", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "current" in data
        assert data["current"]["is_enabled"] is True
        assert data["current"]["threshold"] == 0.85
        assert data["current"]["max_cost"] == 2.5
        assert data["current"]["max_retries"] == 3

    def test_update_modifies_runtime_settings(self, client: TestClient, db_session):
        """PUT updates runtime_settings (not module-level constants)."""
        from config import runtime_settings

        # Save original values to restore after test
        orig_enabled = runtime_settings.auto_edit_enabled
        orig_threshold = runtime_settings.auto_edit_threshold
        orig_cost = runtime_settings.auto_edit_max_cost
        orig_retries = runtime_settings.auto_edit_max_retries

        try:
            update_data = {
                "enabled": True,
                "threshold": 0.9,
                "max_cost": 5.0,
                "max_retries": 5,
            }
            put_resp = client.put("/api/admin/settings/auto-edit", json=update_data)
            assert put_resp.status_code == 200

            # Verify runtime_settings was updated
            assert runtime_settings.auto_edit_enabled is True
            assert runtime_settings.auto_edit_threshold == 0.9
            assert runtime_settings.auto_edit_max_cost == 5.0
            assert runtime_settings.auto_edit_max_retries == 5
        finally:
            # Restore original values to avoid polluting other tests
            runtime_settings.auto_edit_enabled = orig_enabled
            runtime_settings.auto_edit_threshold = orig_threshold
            runtime_settings.auto_edit_max_cost = orig_cost
            runtime_settings.auto_edit_max_retries = orig_retries

    def test_update_auto_edit_missing_fields(self, client: TestClient, db_session):
        """PUT with missing required fields returns 422."""
        # Missing max_retries
        incomplete = {
            "enabled": True,
            "threshold": 0.8,
            "max_cost": 1.0,
        }
        response = client.put("/api/admin/settings/auto-edit", json=incomplete)
        assert response.status_code == 422

    def test_update_auto_edit_invalid_types(self, client: TestClient, db_session):
        """PUT with wrong types returns 422."""
        invalid = {
            "enabled": "not_a_bool",
            "threshold": "not_a_float",
            "max_cost": "not_a_float",
            "max_retries": "not_an_int",
        }
        response = client.put("/api/admin/settings/auto-edit", json=invalid)
        assert response.status_code == 422


class TestCostSummary:
    """Test GET /settings/auto-edit/cost-summary endpoint."""

    def test_cost_summary_empty(self, client: TestClient, db_session):
        """Cost summary with no activity logs returns zeros."""
        response = client.get("/api/admin/settings/auto-edit/cost-summary")
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
        now = datetime.now(UTC)

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

        response = client.get("/api/admin/settings/auto-edit/cost-summary")
        assert response.status_code == 200
        data = response.json()

        assert data["today"] == 0.15
        assert data["edit_count_today"] == 2
        assert data["total"] == 0.15

    def test_cost_summary_old_data_excluded_from_today(self, client: TestClient, db_session):
        """Old activity logs excluded from today count but included in total."""
        now = datetime.now(UTC)
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

        response = client.get("/api/admin/settings/auto-edit/cost-summary")
        assert response.status_code == 200
        data = response.json()

        assert data["today"] == 0.05
        assert data["edit_count_today"] == 1
        assert data["total"] == 0.25
