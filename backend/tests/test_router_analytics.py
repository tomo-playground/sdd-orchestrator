"""Tests for analytics router endpoints."""

from fastapi.testclient import TestClient

from models.activity_log import ActivityLog
from models.group import Group
from models.project import Project
from models.scene import Scene
from models.storyboard import Storyboard


def _ensure_hierarchy(db_session, storyboard_id=1):
    """Create minimal hierarchy for FK validity."""
    if not db_session.query(Storyboard).filter(Storyboard.id == storyboard_id).first():
        if not db_session.query(Project).first():
            db_session.add(Project(id=1, name="Test Project"))
            db_session.flush()
        if not db_session.query(Group).first():
            db_session.add(Group(id=1, name="Test Group", project_id=1))
            db_session.flush()
        sb = Storyboard(id=storyboard_id, title="Test", group_id=1)
        db_session.add(sb)
        db_session.flush()
    if not db_session.query(Scene).filter(Scene.storyboard_id == storyboard_id).first():
        db_session.add(Scene(storyboard_id=storyboard_id, order=0, script="s0"))
        db_session.flush()
    return db_session.query(Scene).filter(Scene.storyboard_id == storyboard_id).first().id


def _create_activity_log(db_session, **kwargs):
    """Helper to insert an activity log."""
    sb_id = kwargs.get("storyboard_id", 1)
    scene_id = _ensure_hierarchy(db_session, storyboard_id=sb_id)
    defaults = {
        "storyboard_id": sb_id,
        "scene_id": scene_id,
        "prompt": "1girl, smile",
        "status": "success",
    }
    defaults.update(kwargs)
    if "scene_id" not in kwargs:
        defaults["scene_id"] = scene_id
    log = ActivityLog(**defaults)
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    return log


class TestGeminiEditAnalytics:
    """Test GET /analytics/gemini-edits endpoint."""

    def test_empty_analytics(self, client: TestClient, db_session):
        """Return zero stats when no edits exist."""
        resp = client.get("/api/admin/analytics/gemini-edits")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_edits"] == 0
        assert data["avg_cost_usd"] == 0
        assert data["total_cost_usd"] == 0
        assert data["avg_improvement"] == 0
        assert data["edits"] == []

    def test_analytics_with_edits(self, client: TestClient, db_session):
        """Return correct statistics for gemini edits."""
        _create_activity_log(
            db_session,
            gemini_edited=True,
            gemini_cost_usd=0.04,
            original_match_rate=0.60,
            final_match_rate=0.85,
        )
        _create_activity_log(
            db_session,
            gemini_edited=True,
            gemini_cost_usd=0.05,
            original_match_rate=0.50,
            final_match_rate=0.80,
        )
        # Non-gemini log should be excluded
        _create_activity_log(db_session, gemini_edited=False)

        resp = client.get("/api/admin/analytics/gemini-edits")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_edits"] == 2
        assert data["total_cost_usd"] == 0.09
        assert data["avg_cost_usd"] == 0.045
        assert len(data["edits"]) == 2

    def test_analytics_improvement_ranges(self, client: TestClient, db_session):
        """Verify improvement range buckets."""
        # 5% improvement -> "0-10%" bucket
        _create_activity_log(
            db_session,
            gemini_edited=True,
            original_match_rate=0.70,
            final_match_rate=0.75,
            gemini_cost_usd=0.01,
        )
        # 15% improvement -> "10-20%" bucket
        _create_activity_log(
            db_session,
            gemini_edited=True,
            original_match_rate=0.60,
            final_match_rate=0.75,
            gemini_cost_usd=0.02,
        )
        # 35% improvement -> "30%+" bucket
        _create_activity_log(
            db_session,
            gemini_edited=True,
            original_match_rate=0.40,
            final_match_rate=0.75,
            gemini_cost_usd=0.03,
        )

        resp = client.get("/api/admin/analytics/gemini-edits")
        data = resp.json()
        ranges = data["by_improvement_range"]
        assert ranges["0-10%"] == 1
        assert ranges["10-20%"] == 1
        assert ranges["30%+"] == 1

    def test_analytics_filter_by_storyboard(self, client: TestClient, db_session):
        """Filter analytics to a specific storyboard."""
        _create_activity_log(db_session, storyboard_id=1, gemini_edited=True, gemini_cost_usd=0.01)
        _create_activity_log(db_session, storyboard_id=2, gemini_edited=True, gemini_cost_usd=0.02)

        resp = client.get("/api/admin/analytics/gemini-edits", params={"storyboard_id": 1})
        data = resp.json()
        assert data["total_edits"] == 1


class TestGeminiEditSummary:
    """Test GET /analytics/gemini-edits/summary endpoint."""

    def test_empty_summary(self, client: TestClient, db_session):
        """Return zero stats when no edits exist."""
        resp = client.get("/api/admin/analytics/gemini-edits/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_edits"] == 0
        assert data["total_cost"] == 0
        assert data["success_rate"] == 0
        assert data["avg_improvement"] == 0

    def test_summary_with_data(self, client: TestClient, db_session):
        """Return correct summary stats."""
        # Successful edit: final > original
        _create_activity_log(
            db_session,
            gemini_edited=True,
            gemini_cost_usd=0.04,
            original_match_rate=0.60,
            final_match_rate=0.85,
        )
        # Failed edit: final < original
        _create_activity_log(
            db_session,
            gemini_edited=True,
            gemini_cost_usd=0.03,
            original_match_rate=0.70,
            final_match_rate=0.65,
        )

        resp = client.get("/api/admin/analytics/gemini-edits/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_edits"] == 2
        assert data["total_cost"] == 0.07
        assert data["success_rate"] == 0.5  # 1 of 2 improved
