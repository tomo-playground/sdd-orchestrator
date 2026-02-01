"""Tests for activity_logs router endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from models.activity_log import ActivityLog
from models.tag import Tag, TagRule


def _create_log(db_session, **kwargs):
    """Helper to insert an activity log."""
    defaults = dict(
        storyboard_id=1,
        scene_id=0,
        prompt="1girl, smile",
        status="success",
    )
    defaults.update(kwargs)
    log = ActivityLog(**defaults)
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    return log


def _create_tag(db_session, name, **kwargs):
    """Helper to insert a tag."""
    defaults = dict(name=name, category="general", priority=100, default_layer=0, usage_scope="ANY")
    defaults.update(kwargs)
    tag = Tag(**defaults)
    db_session.add(tag)
    db_session.commit()
    db_session.refresh(tag)
    return tag


class TestCreateActivityLog:
    """Test POST /activity-logs."""

    @patch("services.validation._extract_storage_key", return_value="projects/1/images/scene_0.png")
    def test_create_log(self, mock_extract, client: TestClient, db_session):
        """Create a basic activity log."""
        resp = client.post("/activity-logs", json={
            "storyboard_id": 1,
            "scene_id": 0,
            "prompt": "1girl, smile",
            "tags": ["1girl", "smile"],
            "match_rate": 0.85,
            "status": "success",
            "image_url": "/outputs/scene_0.png",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["scene_id"] == 0
        assert data["status"] == "success"
        assert data["match_rate"] == 0.85

    def test_create_log_minimal(self, client: TestClient, db_session):
        """Create a log with minimal fields."""
        resp = client.post("/activity-logs", json={
            "scene_id": 0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"


class TestGetStoryboardLogs:
    """Test GET /activity-logs/storyboard/{storyboard_id}."""

    def test_get_logs_empty(self, client: TestClient, db_session):
        """Return empty list for storyboard without logs."""
        resp = client.get("/activity-logs/storyboard/999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["logs"] == []
        assert data["total"] == 0

    def test_get_logs(self, client: TestClient, db_session):
        """Return logs for a storyboard."""
        _create_log(db_session, storyboard_id=1, scene_id=0)
        _create_log(db_session, storyboard_id=1, scene_id=1)
        _create_log(db_session, storyboard_id=2, scene_id=0)

        resp = client.get("/activity-logs/storyboard/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_get_logs_filter_status(self, client: TestClient, db_session):
        """Filter logs by status."""
        _create_log(db_session, storyboard_id=1, status="success")
        _create_log(db_session, storyboard_id=1, status="fail")

        resp = client.get("/activity-logs/storyboard/1", params={"status": "fail"})
        data = resp.json()
        assert data["total"] == 1
        assert data["logs"][0]["status"] == "fail"

    def test_get_logs_v2_alias(self, client: TestClient, db_session):
        """V2 alias endpoint returns same data."""
        _create_log(db_session, storyboard_id=1)
        resp = client.get("/activity-logs/1/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1


class TestUpdateLogStatus:
    """Test PATCH /activity-logs/{log_id}/status."""

    def test_update_status(self, client: TestClient, db_session):
        """Update a log's status."""
        log = _create_log(db_session, status="pending")
        resp = client.patch(f"/activity-logs/{log.id}/status", json={"status": "success"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_update_status_not_found(self, client: TestClient, db_session):
        """Return 404 for non-existent log."""
        resp = client.patch("/activity-logs/9999/status", json={"status": "success"})
        assert resp.status_code == 404


class TestDeleteLog:
    """Test DELETE /activity-logs/{log_id}."""

    def test_delete_log(self, client: TestClient, db_session):
        """Delete an activity log."""
        log = _create_log(db_session)
        resp = client.delete(f"/activity-logs/{log.id}")
        assert resp.status_code == 200
        assert db_session.query(ActivityLog).filter(ActivityLog.id == log.id).first() is None

    def test_delete_log_not_found(self, client: TestClient, db_session):
        """Return 404 for non-existent log."""
        resp = client.delete("/activity-logs/9999")
        assert resp.status_code == 404


class TestAnalyzePatterns:
    """Test GET /activity-logs/analyze/patterns."""

    def test_analyze_empty(self, client: TestClient, db_session):
        """Return empty results for storyboard without logs."""
        resp = client.get("/activity-logs/analyze/patterns", params={"storyboard_id": 999})
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_logs"] == 0

    def test_analyze_with_logs(self, client: TestClient, db_session):
        """Return pattern analysis for storyboard."""
        for i in range(5):
            _create_log(
                db_session,
                storyboard_id=1,
                scene_id=i,
                status="success",
                match_rate=0.85,
                tags_used=["smile", "brown_hair", "classroom"],
            )
        for i in range(3):
            _create_log(
                db_session,
                storyboard_id=1,
                scene_id=10 + i,
                status="fail",
                match_rate=0.40,
                tags_used=["smile", "crying"],
            )

        resp = client.get("/activity-logs/analyze/patterns", params={
            "storyboard_id": 1,
            "min_occurrences": 2,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_logs"] == 8
        assert len(data["tag_stats"]) > 0


class TestSuggestConflictRules:
    """Test GET /activity-logs/suggest-conflict-rules."""

    def test_suggest_empty(self, client: TestClient, db_session):
        """Return empty suggestions when no logs exist."""
        resp = client.get("/activity-logs/suggest-conflict-rules", params={
            "storyboard_id": 999,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["suggested_rules"] == []
        assert data["new_rules_count"] == 0


class TestSuccessCombinations:
    """Test GET /activity-logs/success-combinations."""

    def test_success_combinations_empty(self, client: TestClient, db_session):
        """Return empty when no success logs."""
        resp = client.get("/activity-logs/success-combinations", params={
            "storyboard_id": 999,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_success"] == 0

    def test_success_combinations_with_data(self, client: TestClient, db_session):
        """Return combinations from successful logs."""
        # Create tags in DB so category map works
        _create_tag(db_session, "smile", category="expression")
        _create_tag(db_session, "standing", category="pose")

        for i in range(5):
            _create_log(
                db_session,
                storyboard_id=1,
                scene_id=i,
                status="success",
                match_rate=0.85,
                tags_used=["smile", "standing"],
            )

        resp = client.get("/activity-logs/success-combinations", params={
            "storyboard_id": 1,
            "min_occurrences": 3,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_success"] == 5
        assert data["summary"]["categories_found"] > 0


class TestApplyConflictRules:
    """Test POST /activity-logs/apply-conflict-rules."""

    def test_apply_conflict_rules(self, client: TestClient, db_session):
        """Apply conflict rules from tag pairs."""
        tag1 = _create_tag(db_session, "upper_body")
        tag2 = _create_tag(db_session, "full_body")

        resp = client.post("/activity-logs/apply-conflict-rules", json={
            "rules": [{"tag1": "upper_body", "tag2": "full_body"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["applied_count"] == 2  # Bidirectional

    def test_apply_conflict_rules_tags_not_found(self, client: TestClient, db_session):
        """Skip rules when tags not found in DB."""
        resp = client.post("/activity-logs/apply-conflict-rules", json={
            "rules": [{"tag1": "nonexistent_a", "tag2": "nonexistent_b"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["skipped_count"] == 1

    def test_apply_duplicate_rule(self, client: TestClient, db_session):
        """Skip already existing conflict rules."""
        tag1 = _create_tag(db_session, "upper_body")
        tag2 = _create_tag(db_session, "full_body")

        # Create existing rule
        rule = TagRule(source_tag_id=tag1.id, target_tag_id=tag2.id, rule_type="conflict")
        db_session.add(rule)
        db_session.commit()

        resp = client.post("/activity-logs/apply-conflict-rules", json={
            "rules": [{"tag1": "upper_body", "tag2": "full_body"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["skipped_count"] == 1
