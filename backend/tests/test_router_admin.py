"""Tests for admin router endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from models import Tag


class TestRefreshCaches:
    """Test POST /admin/refresh-caches endpoint.

    The refresh_all_caches function imports all caches from
    services.keywords.db_cache. We patch at the source module level.
    """

    def test_refresh_caches_success(self, client: TestClient, db_session):
        """Cache refresh succeeds with mocked cache classes."""
        with (
            patch("services.keywords.db_cache.TagCategoryCache") as mock_cat,
            patch("services.keywords.db_cache.TagFilterCache") as mock_filter,
            patch("services.keywords.db_cache.TagAliasCache") as mock_alias,
            patch("services.keywords.db_cache.TagRuleCache") as mock_rule,
        ):
            response = client.post("/admin/refresh-caches")
            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert "refreshed" in data["message"].lower()

            # Verify all caches were refreshed
            mock_cat.refresh.assert_called_once()
            mock_filter.refresh.assert_called_once()
            mock_alias.refresh.assert_called_once()
            mock_rule.refresh.assert_called_once()

    def test_refresh_caches_error(self, client: TestClient, db_session):
        """Cache refresh handles partial failures with 207 Multi-Status."""
        with patch("services.keywords.db_cache.TagCategoryCache") as mock_cat:
            mock_cat.refresh.side_effect = RuntimeError("DB connection failed")

            response = client.post("/admin/refresh-caches")
            assert response.status_code == 207
            data = response.json()

            assert data["success"] is False
            assert "failures" in data


class TestDeprecatedTags:
    """Test GET /admin/tags/deprecated endpoint."""

    def test_get_deprecated_tags_empty(self, client: TestClient, db_session):
        """No deprecated tags returns empty list."""
        response = client.get("/admin/tags/deprecated")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["tags"] == []

    def test_get_deprecated_tags_with_data(self, client: TestClient, db_session):
        """Returns deprecated tags correctly."""
        active_tag = Tag(name="active_tag", category="test", is_active=True)
        deprecated_tag = Tag(
            name="deprecated_tag",
            category="test",
            is_active=False,
            deprecated_reason="Replaced by better tag",
        )
        db_session.add_all([active_tag, deprecated_tag])
        db_session.commit()

        response = client.get("/admin/tags/deprecated")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert len(data["tags"]) == 1
        assert data["tags"][0]["name"] == "deprecated_tag"
        assert data["tags"][0]["deprecated_reason"] == "Replaced by better tag"

    def test_get_deprecated_tags_with_replacement(self, client: TestClient, db_session):
        """Deprecated tag with replacement shows replacement info."""
        replacement = Tag(name="new_tag", category="test", is_active=True)
        db_session.add(replacement)
        db_session.flush()

        deprecated = Tag(
            name="old_tag",
            category="test",
            is_active=False,
            deprecated_reason="Use new_tag instead",
            replacement_tag_id=replacement.id,
        )
        db_session.add(deprecated)
        db_session.commit()

        response = client.get("/admin/tags/deprecated")
        data = response.json()

        assert data["total"] == 1
        tag_data = data["tags"][0]
        assert tag_data["replacement"] is not None
        assert tag_data["replacement"]["name"] == "new_tag"
        assert tag_data["replacement"]["id"] == replacement.id


class TestDeprecateTag:
    """Test PUT /admin/tags/{tag_id}/deprecate endpoint."""

    def test_deprecate_tag_success(self, client: TestClient, db_session):
        """Deprecate an active tag."""
        tag = Tag(name="to_deprecate", category="test", is_active=True)
        db_session.add(tag)
        db_session.commit()
        tag_id = tag.id

        request_data = {
            "deprecated_reason": "No longer relevant",
        }

        response = client.put(f"/admin/tags/{tag_id}/deprecate", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["tag"]["is_active"] is False
        assert data["tag"]["deprecated_reason"] == "No longer relevant"

    def test_deprecate_tag_with_replacement(self, client: TestClient, db_session):
        """Deprecate tag and set replacement."""
        replacement = Tag(name="replacement_tag", category="test", is_active=True)
        target = Tag(name="old_tag", category="test", is_active=True)
        db_session.add_all([replacement, target])
        db_session.commit()

        request_data = {
            "deprecated_reason": "Replaced",
            "replacement_tag_id": replacement.id,
        }

        response = client.put(f"/admin/tags/{target.id}/deprecate", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert data["tag"]["replacement_tag_id"] == replacement.id

    def test_deprecate_tag_not_found(self, client: TestClient, db_session):
        """Deprecating non-existent tag returns 404."""
        request_data = {
            "deprecated_reason": "Test",
        }

        response = client.put("/admin/tags/99999/deprecate", json=request_data)
        assert response.status_code == 404

    def test_deprecate_tag_invalid_replacement(self, client: TestClient, db_session):
        """Deprecating with non-existent replacement returns 400."""
        tag = Tag(name="test_tag", category="test", is_active=True)
        db_session.add(tag)
        db_session.commit()

        request_data = {
            "deprecated_reason": "Test",
            "replacement_tag_id": 99999,
        }

        response = client.put(f"/admin/tags/{tag.id}/deprecate", json=request_data)
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_deprecate_tag_self_replacement(self, client: TestClient, db_session):
        """Cannot replace tag with itself."""
        tag = Tag(name="self_tag", category="test", is_active=True)
        db_session.add(tag)
        db_session.commit()

        request_data = {
            "deprecated_reason": "Test",
            "replacement_tag_id": tag.id,
        }

        response = client.put(f"/admin/tags/{tag.id}/deprecate", json=request_data)
        assert response.status_code == 400
        assert "itself" in response.json()["detail"].lower()

    def test_deprecate_tag_missing_reason(self, client: TestClient, db_session):
        """Deprecating without reason returns 422."""
        tag = Tag(name="missing_reason", category="test", is_active=True)
        db_session.add(tag)
        db_session.commit()

        response = client.put(f"/admin/tags/{tag.id}/deprecate", json={})
        assert response.status_code == 422


class TestActivateTag:
    """Test PUT /admin/tags/{tag_id}/activate endpoint."""

    def test_activate_tag_success(self, client: TestClient, db_session):
        """Reactivate a deprecated tag."""
        tag = Tag(
            name="to_activate",
            category="test",
            is_active=False,
            deprecated_reason="Was deprecated",
            replacement_tag_id=None,
        )
        db_session.add(tag)
        db_session.commit()
        tag_id = tag.id

        response = client.put(f"/admin/tags/{tag_id}/activate")
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["tag"]["is_active"] is True

        # Verify deprecation fields cleared in DB
        db_session.refresh(tag)
        assert tag.deprecated_reason is None
        assert tag.replacement_tag_id is None

    def test_activate_tag_not_found(self, client: TestClient, db_session):
        """Activating non-existent tag returns 404."""
        response = client.put("/admin/tags/99999/activate")
        assert response.status_code == 404

    def test_activate_already_active_tag(self, client: TestClient, db_session):
        """Activating an already active tag succeeds (idempotent)."""
        tag = Tag(name="already_active", category="test", is_active=True)
        db_session.add(tag)
        db_session.commit()

        response = client.put(f"/admin/tags/{tag.id}/activate")
        assert response.status_code == 200
        assert response.json()["tag"]["is_active"] is True
