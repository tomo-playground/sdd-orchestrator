"""Tests for avatar router endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

PATCH_PREFIX = "routers.avatar"


class TestAvatarRegenerate:
    """Test POST /avatar/regenerate."""

    @patch(f"{PATCH_PREFIX}.ensure_avatar_file", new_callable=AsyncMock, return_value="shared/avatars/avatar_abc123.png")
    @patch(f"{PATCH_PREFIX}.get_storage")
    def test_regenerate_success(self, mock_storage_fn, mock_ensure, client: TestClient):
        """Regenerate an avatar successfully."""
        mock_storage = MagicMock()
        mock_storage.exists.return_value = True
        mock_storage.delete.return_value = None
        mock_storage_fn.return_value = mock_storage

        resp = client.post("/avatar/regenerate", json={"avatar_key": "test_channel"})
        assert resp.status_code == 200
        data = resp.json()
        assert "filename" in data
        assert data["filename"] == "avatar_abc123.png"

    @patch(f"{PATCH_PREFIX}.ensure_avatar_file", new_callable=AsyncMock, return_value=None)
    @patch(f"{PATCH_PREFIX}.get_storage")
    def test_regenerate_failure(self, mock_storage_fn, mock_ensure, client: TestClient):
        """Return 500 when regeneration fails."""
        mock_storage = MagicMock()
        mock_storage.exists.return_value = False
        mock_storage_fn.return_value = mock_storage

        resp = client.post("/avatar/regenerate", json={"avatar_key": "test_channel"})
        assert resp.status_code == 500

    def test_regenerate_empty_key(self, client: TestClient):
        """Return 400 for empty avatar key."""
        resp = client.post("/avatar/regenerate", json={"avatar_key": "   "})
        assert resp.status_code == 400

    @patch(f"{PATCH_PREFIX}.ensure_avatar_file", new_callable=AsyncMock, return_value="shared/avatars/avatar_newfile.png")
    @patch(f"{PATCH_PREFIX}.get_storage")
    def test_regenerate_no_existing_file(self, mock_storage_fn, mock_ensure, client: TestClient):
        """Regenerate when no existing file (skip delete)."""
        mock_storage = MagicMock()
        mock_storage.exists.return_value = False
        mock_storage_fn.return_value = mock_storage

        resp = client.post("/avatar/regenerate", json={"avatar_key": "new_channel"})
        assert resp.status_code == 200
        # delete should not be called when file does not exist
        mock_storage.delete.assert_not_called()


class TestAvatarResolve:
    """Test POST /avatar/resolve."""

    @patch(f"{PATCH_PREFIX}.get_storage")
    def test_resolve_existing(self, mock_storage_fn, client: TestClient):
        """Resolve an existing avatar."""
        mock_storage = MagicMock()
        mock_storage.exists.return_value = True
        mock_storage_fn.return_value = mock_storage

        resp = client.post("/avatar/resolve", json={"avatar_key": "test_channel"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] is not None
        assert data["filename"].startswith("avatar_")

    @patch(f"{PATCH_PREFIX}.get_storage")
    def test_resolve_not_found(self, mock_storage_fn, client: TestClient):
        """Return null filename when avatar does not exist."""
        mock_storage = MagicMock()
        mock_storage.exists.return_value = False
        mock_storage_fn.return_value = mock_storage

        resp = client.post("/avatar/resolve", json={"avatar_key": "nonexistent"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] is None

    def test_resolve_empty_key(self, client: TestClient):
        """Return 400 for empty avatar key."""
        resp = client.post("/avatar/resolve", json={"avatar_key": "  "})
        assert resp.status_code == 400
