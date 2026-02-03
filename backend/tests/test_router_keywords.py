"""Tests for keywords router endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from models import Tag


class TestKeywordPriority:
    """Test GET /keywords/priority endpoint."""

    def test_get_priority(self, client: TestClient):
        """Returns keyword category priorities and patterns."""
        response = client.get("/keywords/priority")
        assert response.status_code == 200
        data = response.json()

        assert "priority" in data
        assert "patterns" in data
        assert isinstance(data["priority"], dict)
        assert isinstance(data["patterns"], dict)


class TestKeywordSuggestions:
    """Test GET /keywords/suggestions endpoint."""

    @patch("routers.keywords.load_keyword_suggestions")
    def test_suggestions_default_params(self, mock_load, client: TestClient):
        """Load suggestions with default parameters."""
        mock_load.return_value = [
            {"tag": "smile", "count": 10, "suggested_category": "expression"},
        ]
        response = client.get("/keywords/suggestions")
        assert response.status_code == 200
        data = response.json()

        assert data["min_count"] == 3
        assert data["limit"] == 50
        assert isinstance(data["suggestions"], list)
        mock_load.assert_called_once_with(min_count=3, limit=50)

    @patch("routers.keywords.load_keyword_suggestions")
    def test_suggestions_custom_params(self, mock_load, client: TestClient):
        """Load suggestions with custom min_count and limit."""
        mock_load.return_value = []
        response = client.get("/keywords/suggestions?min_count=5&limit=20")
        assert response.status_code == 200
        data = response.json()

        assert data["min_count"] == 5
        assert data["limit"] == 20
        mock_load.assert_called_once_with(min_count=5, limit=20)


class TestKeywordCategories:
    """Test GET /keywords/categories endpoint."""

    @patch("routers.keywords.load_tags_from_db")
    def test_categories_success(self, mock_load, client: TestClient):
        """Returns grouped categories."""
        mock_load.return_value = {
            "expression": ["smile", "angry", "crying"],
            "pose": ["standing", "sitting"],
        }
        response = client.get("/keywords/categories")
        assert response.status_code == 200
        data = response.json()

        assert "categories" in data
        assert "expression" in data["categories"]
        assert len(data["categories"]["expression"]) == 3

    @patch("routers.keywords.load_tags_from_db")
    def test_categories_error_returns_500(self, mock_load, client: TestClient):
        """Service failure returns 500."""
        mock_load.side_effect = RuntimeError("DB connection failed")
        response = client.get("/keywords/categories")
        assert response.status_code == 500


class TestListTags:
    """Test GET /keywords/tags endpoint."""

    def test_list_tags_empty(self, client: TestClient, db_session):
        """List tags when DB is empty."""
        response = client.get("/keywords/tags")
        assert response.status_code == 200
        data = response.json()

        assert data["tags"] == []
        assert data["total"] == 0
        assert data["limit"] == 100
        assert data["offset"] == 0

    def test_list_tags_with_data(self, client: TestClient, db_session):
        """List tags returns DB tags."""
        tag1 = Tag(name="smile", category="scene", default_layer=5)
        tag2 = Tag(name="standing", category="scene", default_layer=7)
        db_session.add_all([tag1, tag2])
        db_session.commit()

        response = client.get("/keywords/tags")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["tags"]) == 2
        tag_names = [t["tag"] for t in data["tags"]]
        assert "smile" in tag_names
        assert "standing" in tag_names

    def test_list_tags_search_filter(self, client: TestClient, db_session):
        """Search filter narrows results."""
        tag1 = Tag(name="brown_hair", category="character", default_layer=3)
        tag2 = Tag(name="brown_eyes", category="character", default_layer=3)
        tag3 = Tag(name="smile", category="scene", default_layer=5)
        db_session.add_all([tag1, tag2, tag3])
        db_session.commit()

        response = client.get("/keywords/tags?search=brown")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        tag_names = [t["tag"] for t in data["tags"]]
        assert "brown_hair" in tag_names
        assert "brown_eyes" in tag_names
        assert "smile" not in tag_names

    def test_list_tags_category_filter(self, client: TestClient, db_session):
        """Category filter by layer number."""
        tag1 = Tag(name="smile", category="scene", default_layer=5)
        tag2 = Tag(name="standing", category="scene", default_layer=7)
        db_session.add_all([tag1, tag2])
        db_session.commit()

        response = client.get("/keywords/tags?category=layer_5")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["tags"][0]["tag"] == "smile"

    def test_list_tags_pagination(self, client: TestClient, db_session):
        """Pagination limit and offset work."""
        for i in range(5):
            db_session.add(Tag(name=f"tag_{i:02d}", category="scene", default_layer=0))
        db_session.commit()

        response = client.get("/keywords/tags?limit=2&offset=1")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert len(data["tags"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 1

    def test_list_tags_invalid_category(self, client: TestClient, db_session):
        """Invalid category format returns all tags."""
        tag = Tag(name="smile", category="scene", default_layer=5)
        db_session.add(tag)
        db_session.commit()

        response = client.get("/keywords/tags?category=invalid_format")
        assert response.status_code == 200
        data = response.json()
        # Invalid category is ignored, returns all tags
        assert data["total"] == 1


class TestApproveKeyword:
    """Test POST /keywords/approve endpoint."""

    def test_approve_new_tag(self, client: TestClient, db_session):
        """Approve adds new tag to DB."""
        request_data = {"tag": "new_expression", "category": "expression"}
        response = client.post("/keywords/approve", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["ok"] is True
        assert data["tag"] == "new_expression"
        assert data["category"] == "expression"

        # Verify in DB
        tag = db_session.query(Tag).filter(Tag.name == "new_expression").first()
        assert tag is not None
        assert tag.group_name == "expression"

    def test_approve_existing_tag(self, client: TestClient, db_session):
        """Approving existing tag returns success with message."""
        existing = Tag(name="smile", category="scene")
        db_session.add(existing)
        db_session.commit()

        request_data = {"tag": "smile", "category": "expression"}
        response = client.post("/keywords/approve", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["ok"] is True
        assert "already exists" in data.get("message", "").lower()

    def test_approve_empty_tag(self, client: TestClient, db_session):
        """Empty tag string returns 400."""
        request_data = {"tag": "", "category": "expression"}
        response = client.post("/keywords/approve", json=request_data)
        assert response.status_code == 400

    def test_approve_empty_category(self, client: TestClient, db_session):
        """Empty category returns 400."""
        request_data = {"tag": "smile", "category": ""}
        response = client.post("/keywords/approve", json=request_data)
        assert response.status_code == 400


class TestEffectiveness:
    """Test GET /keywords/effectiveness endpoints."""

    @patch("routers.keywords.get_tag_effectiveness_report")
    @patch("routers.keywords.get_effective_tags")
    def test_effectiveness_report(self, mock_effective, mock_report, client: TestClient):
        """Returns effectiveness report with summary."""
        mock_report.return_value = [
            {"tag": "smile", "match_rate": 0.85, "total": 10},
        ]
        mock_effective.return_value = {
            "high": ["smile"],
            "medium": ["standing"],
            "low": ["complex_action"],
            "unknown": [],
        }

        response = client.get("/keywords/effectiveness")
        assert response.status_code == 200
        data = response.json()

        assert "summary" in data
        assert data["summary"]["high_effectiveness"] == 1
        assert data["summary"]["medium_effectiveness"] == 1
        assert data["summary"]["low_effectiveness"] == 1
        assert isinstance(data["tags"], list)

    @patch("routers.keywords.get_effective_tags")
    def test_effectiveness_summary(self, mock_effective, client: TestClient):
        """Returns summarized effectiveness."""
        mock_effective.return_value = {
            "high": ["smile", "standing"],
            "medium": [],
            "low": [],
            "unknown": ["rare_tag"],
        }

        response = client.get("/keywords/effectiveness/summary")
        assert response.status_code == 200
        data = response.json()
        assert "high" in data
        assert len(data["high"]) == 2

    @patch("routers.keywords.get_tag_effectiveness_report")
    @patch("routers.keywords.get_effective_tags")
    def test_effectiveness_error_returns_500(self, mock_eff, mock_report, client: TestClient):
        """Service error returns 500."""
        mock_report.side_effect = RuntimeError("File not found")
        mock_eff.return_value = {}

        response = client.get("/keywords/effectiveness")
        assert response.status_code == 500


class TestBatchApprove:
    """Test batch approve endpoints."""

    @patch("routers.keywords.load_keyword_suggestions")
    def test_batch_approve_preview(self, mock_load, client: TestClient):
        """Preview returns grouped tags."""
        mock_load.return_value = [
            {"tag": "smile", "suggested_category": "expression", "confidence": 0.9},
            {"tag": "nsfw_tag", "suggested_category": "skip", "confidence": 0.95},
            {"tag": "ambiguous", "suggested_category": "pose", "confidence": 0.3},
        ]
        response = client.get("/keywords/batch-approve/preview")
        assert response.status_code == 200
        data = response.json()

        assert data["ready_count"] == 1
        assert data["skip_count"] == 1
        assert data["manual_count"] == 1

    @patch("routers.keywords.load_keyword_suggestions")
    def test_batch_approve_preview_custom_confidence(self, mock_load, client: TestClient):
        """Preview respects min_confidence parameter."""
        mock_load.return_value = [
            {"tag": "tag1", "suggested_category": "expression", "confidence": 0.6},
            {"tag": "tag2", "suggested_category": "pose", "confidence": 0.8},
        ]
        response = client.get("/keywords/batch-approve/preview?min_confidence=0.5")
        assert response.status_code == 200
        data = response.json()
        assert data["ready_count"] == 2

    @patch("routers.keywords.load_keyword_suggestions")
    def test_batch_approve_specific_tags(self, mock_load, client: TestClient, db_session):
        """Batch approve specific tags by name."""
        mock_load.return_value = [
            {"tag": "new_smile", "suggested_category": "expression", "confidence": 0.9},
            {"tag": "new_pose", "suggested_category": "pose", "confidence": 0.8},
        ]
        request_data = {"tags": ["new_smile"]}
        response = client.post("/keywords/batch-approve", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["ok"] is True
        assert data["approved_count"] == 1

    @patch("routers.keywords.load_keyword_suggestions")
    def test_batch_approve_auto_confidence(self, mock_load, client: TestClient, db_session):
        """Batch approve all tags above confidence threshold."""
        mock_load.return_value = [
            {"tag": "auto_tag", "suggested_category": "expression", "confidence": 0.9},
            {"tag": "low_conf", "suggested_category": "pose", "confidence": 0.3},
        ]
        request_data = {"min_confidence": 0.7}
        response = client.post("/keywords/batch-approve", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["ok"] is True
        assert data["approved_count"] == 1


class TestTagRules:
    """Test GET /keywords/rules endpoint."""

    @patch("routers.keywords.get_tag_rules_summary")
    def test_get_rules(self, mock_summary, client: TestClient):
        """Returns tag rules summary."""
        mock_summary.return_value = {
            "total_rules": 5,
            "conflict_count": 3,
            "requires_count": 2,
        }
        response = client.get("/keywords/rules")
        assert response.status_code == 200
        data = response.json()
        assert data["total_rules"] == 5

    @patch("routers.keywords.get_tag_rules_summary")
    def test_get_rules_error(self, mock_summary, client: TestClient):
        """Service error returns 500."""
        mock_summary.side_effect = RuntimeError("DB error")
        response = client.get("/keywords/rules")
        assert response.status_code == 500


class TestValidateTags:
    """Test POST /keywords/validate endpoint."""

    @patch("routers.keywords.validate_prompt_tags")
    def test_validate_tags_with_conflicts(self, mock_validate, client: TestClient):
        """Tags with conflicts are reported."""
        mock_validate.return_value = {
            "valid": False,
            "conflicts": [{"tag1": "short_hair", "tag2": "long_hair"}],
            "missing_deps": [],
        }
        response = client.post("/keywords/validate", json=["short_hair", "long_hair"])
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["conflicts"]) == 1

    @patch("routers.keywords.validate_prompt_tags")
    def test_validate_tags_clean(self, mock_validate, client: TestClient):
        """Clean tags pass validation."""
        mock_validate.return_value = {
            "valid": True,
            "conflicts": [],
            "missing_deps": [],
        }
        response = client.post("/keywords/validate", json=["smile", "standing"])
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True


class TestSyncEndpoints:
    """Test sync utility endpoints."""

    @patch("routers.keywords.sync_lora_triggers_to_tags")
    def test_sync_lora_triggers(self, mock_sync, client: TestClient):
        """Sync LoRA triggers returns summary."""
        mock_sync.return_value = {
            "summary": {"added_count": 3, "updated_count": 1, "skipped_count": 5},
            "details": [],
        }
        response = client.post("/keywords/sync-lora-triggers")
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["added_count"] == 3

    @patch("routers.keywords.sync_category_patterns_to_tags")
    def test_sync_category_patterns(self, mock_sync, client: TestClient):
        """Sync category patterns returns summary."""
        mock_sync.return_value = {
            "summary": {"added_count": 10, "updated_count": 0, "skipped_count": 50},
            "details": [],
        }
        response = client.post("/keywords/sync-category-patterns")
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["added_count"] == 10

    @patch("routers.keywords.sync_category_patterns_to_tags")
    def test_sync_category_patterns_update_existing(self, mock_sync, client: TestClient):
        """Sync with update_existing parameter."""
        mock_sync.return_value = {
            "summary": {"added_count": 0, "updated_count": 15, "skipped_count": 45},
            "details": [],
        }
        response = client.post("/keywords/sync-category-patterns?update_existing=true")
        assert response.status_code == 200
        mock_sync.assert_called_once_with(update_existing=True)

    @patch("routers.keywords.sync_lora_triggers_to_tags")
    def test_sync_lora_triggers_error(self, mock_sync, client: TestClient):
        """Sync error returns 500."""
        mock_sync.side_effect = RuntimeError("DB error")
        response = client.post("/keywords/sync-lora-triggers")
        assert response.status_code == 500
