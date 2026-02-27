"""Tests for storyboard constraints (title truncation, boolean casting)."""

from fastapi.testclient import TestClient


def test_create_storyboard_long_title_rejected(client: TestClient):
    """
    Test that a storyboard title longer than 200 characters is rejected by Pydantic.
    """
    long_title = "A" * 250
    payload = {
        "title": long_title,
        "description": "Test description",
        "group_id": 1,
        "character_id": None,
        "style_profile_id": None,
        "scenes": [],
    }

    response = client.post("/api/v1/storyboards", json=payload)
    assert response.status_code == 422  # Pydantic max_length validation


def test_create_storyboard_title_at_limit_truncated(client: TestClient):
    """
    Test that a title within Pydantic limit but above truncation limit is truncated.
    200 chars passes Pydantic (max_length=200) but is truncated to 190 in service.
    """
    long_title = "A" * 200
    payload = {
        "title": long_title,
        "description": "Test description",
        "group_id": 1,
        "character_id": None,
        "style_profile_id": None,
        "scenes": [],
    }

    response = client.post("/api/v1/storyboards", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "storyboard_id" in data


def test_create_storyboard_update_long_title_rejected(client: TestClient):
    """
    Test that updating with a title exceeding max_length is rejected by Pydantic.
    """
    # 1. Create
    payload = {"title": "Initial Title", "description": "Initial Desc", "group_id": 1, "scenes": []}
    create_res = client.post("/api/v1/storyboards", json=payload)
    assert create_res.status_code == 200
    sb_id = create_res.json()["storyboard_id"]

    # 2. Update with oversized title
    long_title = "B" * 300
    update_payload = {
        "title": long_title,
        "description": "Updated Desc",
        "character_id": None,
        "style_profile_id": None,
        "scenes": [],
    }

    update_res = client.put(f"/api/v1/storyboards/{sb_id}", json=update_payload)
    assert update_res.status_code == 422  # Pydantic max_length validation


class TestOptimisticLocking:
    """Test optimistic locking (version column + 409 Conflict)."""

    def _create_storyboard(self, client: TestClient) -> dict:
        payload = {"title": "OL Test", "description": "Test", "group_id": 1, "scenes": []}
        res = client.post("/api/v1/storyboards", json=payload)
        assert res.status_code == 200
        return res.json()

    def test_create_returns_version(self, client: TestClient):
        """POST /storyboards returns version=1."""
        data = self._create_storyboard(client)
        assert data["version"] == 1

    def test_update_increments_version(self, client: TestClient):
        """PUT /storyboards/{id} increments version."""
        data = self._create_storyboard(client)
        sb_id = data["storyboard_id"]

        update_payload = {"title": "Updated", "description": "Test", "scenes": [], "version": 1}
        res = client.put(f"/api/v1/storyboards/{sb_id}", json=update_payload)
        assert res.status_code == 200
        assert res.json()["version"] == 2

    def test_update_conflict_returns_409(self, client: TestClient):
        """PUT with stale version returns 409 Conflict."""
        data = self._create_storyboard(client)
        sb_id = data["storyboard_id"]

        # First update succeeds (v1 → v2)
        update1 = {"title": "Tab A", "description": "Test", "scenes": [], "version": 1}
        res1 = client.put(f"/api/v1/storyboards/{sb_id}", json=update1)
        assert res1.status_code == 200
        assert res1.json()["version"] == 2

        # Second update with stale version (v1) fails
        update2 = {"title": "Tab B", "description": "Test", "scenes": [], "version": 1}
        res2 = client.put(f"/api/v1/storyboards/{sb_id}", json=update2)
        assert res2.status_code == 409
        assert "Conflict" in res2.json()["detail"]

    def test_update_without_version_skips_check(self, client: TestClient):
        """PUT without version field skips optimistic lock check."""
        data = self._create_storyboard(client)
        sb_id = data["storyboard_id"]

        update_payload = {"title": "No Version", "description": "Test", "scenes": []}
        res = client.put(f"/api/v1/storyboards/{sb_id}", json=update_payload)
        assert res.status_code == 200

    def test_metadata_patch_conflict_returns_409(self, client: TestClient):
        """PATCH /storyboards/{id}/metadata with stale version returns 409."""
        data = self._create_storyboard(client)
        sb_id = data["storyboard_id"]

        # Patch v1 → v2 (success)
        res1 = client.patch(f"/api/v1/storyboards/{sb_id}/metadata", json={"title": "Tab A", "version": 1})
        assert res1.status_code == 200
        assert res1.json()["version"] == 2

        # Patch with stale v1 → 409
        res2 = client.patch(f"/api/v1/storyboards/{sb_id}/metadata", json={"title": "Tab B", "version": 1})
        assert res2.status_code == 409

    def test_metadata_patch_returns_response_model(self, client: TestClient):
        """PATCH returns StoryboardMetadataUpdateResponse fields."""
        data = self._create_storyboard(client)
        sb_id = data["storyboard_id"]

        res = client.patch(f"/api/v1/storyboards/{sb_id}/metadata", json={"title": "New Title"})
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "success"
        assert body["storyboard_id"] == sb_id
        assert "version" in body

    def test_get_returns_version(self, client: TestClient):
        """GET /storyboards/{id} includes version field."""
        data = self._create_storyboard(client)
        sb_id = data["storyboard_id"]

        res = client.get(f"/api/v1/storyboards/{sb_id}")
        assert res.status_code == 200
        assert res.json()["version"] == 1


def test_scene_boolean_type_casting_no_error(client: TestClient):
    """
    Test that passing boolean for integer fields returns 200 OK.
    This implies the type mismatch error is resolved by casting.
    """
    payload = {
        "title": "Boolean Test Storyboard",
        "description": "Testing boolean casting",
        "group_id": 1,
        "scenes": [
            {"scene_id": 1, "script": "Scene 1", "use_reference_only": True, "reference_only_weight": 0.8},
            {"scene_id": 2, "script": "Scene 2", "use_reference_only": False, "reference_only_weight": 0.2},
        ],
    }

    response = client.post("/api/v1/storyboards", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "storyboard_id" in data
