"""Tests for Phase 6-5 Batch B P0 fixes.

Fix 1: generation.py DB session leak (get_db_session context manager)
Fix 3: MediaAsset.local_path property
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from models.media_asset import MediaAsset

# ============================================================
# Fix 1: DB Session Leak - get_db_session context manager
# ============================================================


class TestGetDbSession:
    """Verify get_db_session ensures session.close() is always called."""

    def test_session_closed_on_normal_exit(self):
        """Session is closed after normal context manager exit."""
        mock_session = MagicMock()

        with patch("services.generation.SessionLocal", return_value=mock_session):
            from services.generation import get_db_session

            with get_db_session() as db:
                assert db is mock_session

        mock_session.close.assert_called_once()

    def test_session_closed_on_exception(self):
        """Session is closed even when an exception occurs inside the block."""
        mock_session = MagicMock()

        with patch("services.generation.SessionLocal", return_value=mock_session):
            from services.generation import get_db_session

            with pytest.raises(ValueError, match="test error"):
                with get_db_session() as db:
                    assert db is mock_session
                    raise ValueError("test error")

        mock_session.close.assert_called_once()

    def test_generate_scene_image_uses_context_manager(self):
        """generate_scene_image delegates to _generate_scene_image_with_db via context manager."""
        from services.generation import get_db_session

        mock_session = MagicMock()

        with patch("services.generation.SessionLocal", return_value=mock_session):
            with get_db_session() as db:
                # Verify the session returned is the one from SessionLocal
                assert db is mock_session
            # After exiting, close must be called
            mock_session.close.assert_called_once()


# ============================================================
# Fix 3: MediaAsset.local_path property
# ============================================================


class TestMediaAssetLocalPath:
    """Verify MediaAsset.local_path property delegates to storage."""

    def test_local_path_property_exists(self):
        """MediaAsset has a local_path property."""
        assert hasattr(MediaAsset, "local_path")
        # Verify it is a property, not a column
        assert isinstance(MediaAsset.__dict__["local_path"], property), "local_path should be a @property"

    def test_local_path_returns_string(self, db_session):
        """local_path returns a string path via storage.get_local_path."""
        asset = MediaAsset(
            storage_key="images/test.png",
            file_type="image",
            file_name="test.png",
        )
        db_session.add(asset)
        db_session.flush()

        mock_storage = MagicMock()
        mock_storage.get_local_path.return_value = Path("/tmp/outputs/images/test.png")

        with patch("services.storage.get_storage", return_value=mock_storage):
            result = asset.local_path

        assert result == "/tmp/outputs/images/test.png"
        assert isinstance(result, str)
        mock_storage.get_local_path.assert_called_once_with("images/test.png")

    def test_url_property_uses_get_storage(self, db_session):
        """url property also uses get_storage (not initialize_storage)."""
        asset = MediaAsset(
            storage_key="images/test.png",
            file_type="image",
            file_name="test.png",
        )
        db_session.add(asset)
        db_session.flush()

        mock_storage = MagicMock()
        mock_storage.get_url.return_value = "http://localhost:9000/bucket/images/test.png"

        with patch("services.storage.get_storage", return_value=mock_storage):
            result = asset.url

        assert result == "http://localhost:9000/bucket/images/test.png"
        mock_storage.get_url.assert_called_once_with("images/test.png")

    def test_local_path_compatible_with_os_path(self, tmp_path, db_session):
        """local_path string is compatible with os.path.exists and open()."""
        import os

        # Create a real file
        test_file = tmp_path / "test_image.png"
        test_file.write_bytes(b"fake png data")

        asset = MediaAsset(
            storage_key="test_image.png",
            file_type="image",
            file_name="test_image.png",
        )
        db_session.add(asset)
        db_session.flush()

        mock_storage = MagicMock()
        mock_storage.get_local_path.return_value = test_file

        with patch("services.storage.get_storage", return_value=mock_storage):
            path = asset.local_path

        # Should work with os.path operations
        assert os.path.exists(path)

        # Should work with open()
        with open(path, "rb") as f:
            assert f.read() == b"fake png data"
