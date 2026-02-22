"""Tests for tags router endpoints."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from models.tag import Tag


class TestTagsCRUD:
    """Test tag CRUD operations."""

    def _create_tag(self, db_session, name="brown_hair", **kwargs):
        """Helper to insert a tag into the test DB."""
        defaults = {
            "name": name,
            "category": "character",
            "group_name": "hair_color",
            "priority": 100,
            "default_layer": 2,
            "usage_scope": "PERMANENT",
        }
        defaults.update(kwargs)
        tag = Tag(**defaults)
        db_session.add(tag)
        db_session.commit()
        db_session.refresh(tag)
        return tag

    # --- GET /tags ---

    def test_list_tags_empty(self, client: TestClient, db_session):
        """Return empty list when no tags exist."""
        resp = client.get("/tags")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_tags(self, client: TestClient, db_session):
        """Return all tags ordered by priority, name."""
        self._create_tag(db_session, "brown_hair", priority=10)
        self._create_tag(db_session, "blue_eyes", category="character", group_name="eye_color", priority=20)
        resp = client.get("/tags")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "brown_hair"

    def test_list_tags_filter_category(self, client: TestClient, db_session):
        """Filter tags by category."""
        self._create_tag(db_session, "smile", category="scene", group_name="expression")
        self._create_tag(db_session, "brown_hair", category="character")
        resp = client.get("/tags", params={"category": "scene"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "smile"

    def test_list_tags_filter_group(self, client: TestClient, db_session):
        """Filter tags by group_name."""
        self._create_tag(db_session, "brown_hair", group_name="hair_color")
        self._create_tag(db_session, "blue_eyes", group_name="eye_color")
        resp = client.get("/tags", params={"group_name": "hair_color"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "brown_hair"

    # --- GET /tags/groups ---

    def test_list_tag_groups(self, client: TestClient, db_session):
        """Return grouped tag counts."""
        self._create_tag(db_session, "brown_hair", category="character", group_name="hair_color")
        self._create_tag(db_session, "blonde_hair", category="character", group_name="hair_color")
        self._create_tag(db_session, "smile", category="scene", group_name="expression")
        resp = client.get("/tags/groups")
        assert resp.status_code == 200
        data = resp.json()
        assert "groups" in data
        groups = data["groups"]
        assert len(groups) == 2
        hair_group = next(g for g in groups if g["group_name"] == "hair_color")
        assert hair_group["count"] == 2

    # --- GET /tags/search ---

    def test_search_tags(self, client: TestClient, db_session):
        """Search tags by partial name match."""
        self._create_tag(db_session, "brown_hair")
        self._create_tag(db_session, "brown_eyes", group_name="eye_color")
        self._create_tag(db_session, "blue_eyes", group_name="eye_color")
        resp = client.get("/tags/search", params={"q": "brown"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_search_tags_with_category_filter(self, client: TestClient, db_session):
        """Search tags filtered by category."""
        self._create_tag(db_session, "smile", category="scene", group_name="expression")
        self._create_tag(db_session, "smiling_face", category="character", group_name="face")
        resp = client.get("/tags/search", params={"q": "smil", "category": "scene"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "smile"

    def test_search_tags_requires_query(self, client: TestClient, db_session):
        """Search endpoint requires non-empty query."""
        resp = client.get("/tags/search")
        assert resp.status_code == 422

    # --- GET /tags/{tag_id} ---

    def test_get_tag_by_id(self, client: TestClient, db_session):
        """Get a single tag by ID."""
        tag = self._create_tag(db_session, "brown_hair")
        resp = client.get(f"/tags/{tag.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "brown_hair"
        assert data["id"] == tag.id

    def test_get_tag_not_found(self, client: TestClient, db_session):
        """Return 404 for non-existent tag."""
        resp = client.get("/tags/9999")
        assert resp.status_code == 404

    # --- POST /tags ---

    def test_create_tag(self, client: TestClient, db_session):
        """Create a new tag."""
        resp = client.post("/tags", json={
            "name": "brown_hair",
            "category": "appearance",
            "group_name": "hair_color",
            "priority": 50,
            "default_layer": 2,
            "usage_scope": "PERMANENT",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "brown_hair"
        assert data["category"] == "appearance"
        assert "id" in data

    def test_create_tag_duplicate(self, client: TestClient, db_session):
        """Reject duplicate tag name."""
        self._create_tag(db_session, "brown_hair")
        resp = client.post("/tags", json={"name": "brown_hair"})
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    # --- PUT /tags/{tag_id} ---

    def test_update_tag(self, client: TestClient, db_session):
        """Update an existing tag."""
        tag = self._create_tag(db_session, "brown_hair")
        resp = client.put(f"/tags/{tag.id}", json={"name": "dark_brown_hair"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "dark_brown_hair"

    def test_update_tag_not_found(self, client: TestClient, db_session):
        """Return 404 when updating non-existent tag."""
        resp = client.put("/tags/9999", json={"name": "x"})
        assert resp.status_code == 404

    # --- DELETE /tags/{tag_id} ---

    def test_delete_tag(self, client: TestClient, db_session):
        """Delete a tag."""
        tag = self._create_tag(db_session, "brown_hair")
        resp = client.delete(f"/tags/{tag.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["deleted"] == "brown_hair"
        # Verify removed from DB
        assert db_session.query(Tag).filter(Tag.id == tag.id).first() is None

    def test_delete_tag_not_found(self, client: TestClient, db_session):
        """Return 404 when deleting non-existent tag."""
        resp = client.delete("/tags/9999")
        assert resp.status_code == 404


class TestTagsClassification:
    """Test tag classification endpoints."""

    def _create_tag(self, db_session, name="test_tag", **kwargs):
        defaults = {"name": name, "category": "scene", "priority": 100, "default_layer": 0, "usage_scope": "ANY"}
        defaults.update(kwargs)
        tag = Tag(**defaults)
        db_session.add(tag)
        db_session.commit()
        db_session.refresh(tag)
        return tag

    # --- POST /tags/classify ---

    @patch("routers.tags.TagClassifier")
    def test_classify_tags(self, mock_cls, client: TestClient, db_session):
        """Classify a batch of tags."""
        mock_instance = MagicMock()
        mock_instance.classify_batch.return_value = (
            {
                "smile": {"group": "expression", "confidence": 0.95, "source": "rule"},
                "brown_hair": {"group": "hair_color", "confidence": 0.90, "source": "db"},
            },
            [],  # no pending tags
        )
        mock_cls.return_value = mock_instance

        resp = client.post("/tags/classify", json={"tags": ["smile", "brown_hair"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["classified"] == 2
        assert data["unknown"] == 0
        assert "smile" in data["results"]
        assert data["results"]["smile"]["group"] == "expression"

    def test_classify_empty_tags(self, client: TestClient, db_session):
        """Empty tags list returns empty result."""
        resp = client.post("/tags/classify", json={"tags": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["classified"] == 0

    def test_classify_too_many_tags(self, client: TestClient, db_session):
        """Reject more than 50 tags."""
        resp = client.post("/tags/classify", json={"tags": [f"tag_{i}" for i in range(51)]})
        assert resp.status_code == 400

    # --- GET /tags/pending ---

    def test_get_pending_classifications(self, client: TestClient, db_session):
        """Return tags needing classification review."""
        self._create_tag(db_session, "unknown_tag", classification_source="unknown", classification_confidence=0.0)
        self._create_tag(db_session, "low_conf_tag", classification_source="danbooru", classification_confidence=0.5)
        self._create_tag(db_session, "manual_tag", classification_source="manual", classification_confidence=1.0)

        resp = client.get("/tags/pending")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        tag_names = [t["name"] for t in data["tags"]]
        assert "unknown_tag" in tag_names
        assert "low_conf_tag" in tag_names
        assert "manual_tag" not in tag_names

    def test_get_pending_filter_by_source(self, client: TestClient, db_session):
        """Filter pending tags by source."""
        self._create_tag(db_session, "unknown_tag", classification_source="unknown")
        self._create_tag(db_session, "llm_tag", classification_source="llm", classification_confidence=0.6)

        resp = client.get("/tags/pending", params={"source": "unknown"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["tags"][0]["name"] == "unknown_tag"

    # --- POST /tags/approve-classification ---

    def test_approve_classification(self, client: TestClient, db_session):
        """Approve a tag classification."""
        tag = self._create_tag(db_session, "test_tag", classification_source="danbooru", classification_confidence=0.5)
        resp = client.post("/tags/approve-classification", json={
            "tag_id": tag.id,
            "group_name": "expression",
            "category": "expression",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["group_name"] == "expression"

        # Verify DB updated
        db_session.refresh(tag)
        assert tag.classification_source == "manual"
        assert tag.classification_confidence == 1.0

    def test_approve_classification_not_found(self, client: TestClient, db_session):
        """Return 404 for non-existent tag."""
        resp = client.post("/tags/approve-classification", json={
            "tag_id": 9999,
            "group_name": "expression",
        })
        assert resp.status_code == 404

    # --- POST /tags/bulk-approve-classifications ---

    def test_bulk_approve(self, client: TestClient, db_session):
        """Bulk approve multiple tag classifications."""
        tag1 = self._create_tag(db_session, "tag_a", classification_source="unknown")
        tag2 = self._create_tag(db_session, "tag_b", classification_source="llm", classification_confidence=0.3)

        resp = client.post("/tags/bulk-approve-classifications", json=[
            {"tag_id": tag1.id, "group_name": "expression"},
            {"tag_id": tag2.id, "group_name": "hair_color"},
        ])
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["approved_count"] == 2
        assert len(data["failed"]) == 0

    def test_bulk_approve_partial_failure(self, client: TestClient, db_session):
        """Bulk approve with some tags not found."""
        tag = self._create_tag(db_session, "real_tag")
        resp = client.post("/tags/bulk-approve-classifications", json=[
            {"tag_id": tag.id, "group_name": "expression"},
            {"tag_id": 9999, "group_name": "pose"},
        ])
        assert resp.status_code == 200
        data = resp.json()
        assert data["approved_count"] == 1
        assert len(data["failed"]) == 1

    def test_bulk_approve_too_many(self, client: TestClient, db_session):
        """Reject more than 100 approvals."""
        approvals = [{"tag_id": i, "group_name": "x"} for i in range(101)]
        resp = client.post("/tags/bulk-approve-classifications", json=approvals)
        assert resp.status_code == 400

    # --- POST /tags/migrate-patterns ---

    @patch("routers.tags.migrate_patterns_to_rules")
    @patch("routers.tags.CATEGORY_PATTERNS", {"hair_color": ["_hair"]}, create=True)
    def test_migrate_patterns(self, mock_migrate, client: TestClient, db_session):
        """Migrate category patterns to classification_rules."""
        mock_migrate.return_value = 5
        resp = client.post("/tags/migrate-patterns")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["rules_created"] == 5
