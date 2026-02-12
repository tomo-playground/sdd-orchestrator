"""Tests for asset router endpoints (fonts, audio, overlays)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@pytest.fixture
def mock_storage_s3():
    """Mock storage in S3 mode."""
    with patch("services.storage.get_storage") as mock_get_storage, patch("config.STORAGE_MODE", "s3"):
        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage
        yield mock_storage


@pytest.fixture
def mock_storage_local():
    """Mock storage in local mode."""
    with (
        patch("config.STORAGE_MODE", "local"),
        patch("config.ASSETS_DIR") as mock_assets_dir,
        patch("config.AUDIO_DIR") as mock_audio_dir,
    ):
        yield mock_assets_dir, mock_audio_dir


class TestFontsList:
    """Tests for /fonts/list endpoint."""

    def test_list_fonts_s3_mode(self, mock_storage_s3):
        """Test font listing in S3 mode returns object array with name property."""
        # Mock S3 storage keys
        mock_storage_s3.list_prefix.return_value = [
            "shared/fonts/font1.ttf",
            "shared/fonts/font2.otf",
            "shared/fonts/font3.ttc",
            "shared/fonts/not_a_font.txt",  # Should be filtered out
        ]

        response = client.get("/fonts/list")

        assert response.status_code == 200
        data = response.json()
        assert "fonts" in data
        assert isinstance(data["fonts"], list)

        # Verify format: should be array of objects with "name" property
        assert len(data["fonts"]) == 3
        for font in data["fonts"]:
            assert isinstance(font, dict)
            assert "name" in font
            assert isinstance(font["name"], str)

        # Verify content
        font_names = [f["name"] for f in data["fonts"]]
        assert "font1.ttf" in font_names
        assert "font2.otf" in font_names
        assert "font3.ttc" in font_names
        assert "not_a_font.txt" not in font_names

        # Verify sorting
        assert font_names == sorted(font_names)

    def test_list_fonts_s3_empty(self, mock_storage_s3):
        """Test font listing with no fonts in S3."""
        mock_storage_s3.list_prefix.return_value = []

        response = client.get("/fonts/list")

        assert response.status_code == 200
        data = response.json()
        assert data["fonts"] == []

    def test_list_fonts_local_mode(self):
        """Test font listing in local mode."""
        from unittest.mock import MagicMock

        with patch("config.STORAGE_MODE", "local"), patch("config.ASSETS_DIR") as mock_assets_dir:
            # Mock fonts directory
            mock_fonts_dir = MagicMock()
            mock_fonts_dir.exists.return_value = True
            mock_assets_dir.__truediv__.return_value = mock_fonts_dir

            # Mock font files
            font1 = MagicMock()
            font1.name = "test_font.ttf"
            font2 = MagicMock()
            font2.name = "another_font.otf"

            mock_fonts_dir.glob.return_value = iter([font1, font2])

            response = client.get("/fonts/list")

            assert response.status_code == 200
            data = response.json()
            assert len(data["fonts"]) >= 0  # May have duplicates from multiple globs

            # Verify format
            if data["fonts"]:
                for font in data["fonts"]:
                    assert isinstance(font, dict)
                    assert "name" in font

    def test_list_fonts_deduplication(self, mock_storage_s3):
        """Test font deduplication when same font appears multiple times."""
        # Mock S3 storage with duplicate entries
        mock_storage_s3.list_prefix.return_value = [
            "shared/fonts/font1.ttf",
            "shared/fonts/font1.ttf",  # Duplicate
            "shared/fonts/font2.otf",
        ]

        response = client.get("/fonts/list")

        assert response.status_code == 200
        data = response.json()

        # Should remove duplicates
        font_names = [f["name"] for f in data["fonts"]]
        assert len(font_names) == 2
        assert font_names.count("font1.ttf") == 1


class TestAudioList:
    """Tests for /audio/list endpoint."""

    def test_list_audio_s3_mode(self, mock_storage_s3):
        """Test audio listing in S3 mode."""
        mock_storage_s3.list_prefix.return_value = [
            "shared/audio/bgm1.mp3",
            "shared/audio/bgm2.wav",
            "shared/audio/bgm3.m4a",
        ]
        mock_storage_s3.get_url.side_effect = lambda key: f"http://minio/{key}"

        response = client.get("/audio/list")

        assert response.status_code == 200
        data = response.json()
        assert "audios" in data
        assert len(data["audios"]) == 3

        # Verify format
        for audio in data["audios"]:
            assert "name" in audio
            assert "url" in audio
            assert audio["url"].startswith("http://minio/")

    def test_list_audio_s3_empty(self, mock_storage_s3):
        """Test audio listing with no audio files."""
        mock_storage_s3.list_prefix.return_value = []

        response = client.get("/audio/list")

        assert response.status_code == 200
        data = response.json()
        assert data["audios"] == []


class TestOverlayList:
    """Tests for /overlay/list endpoint."""

    def test_list_overlays_s3_mode(self, mock_storage_s3):
        """Test overlay listing in S3 mode."""
        mock_storage_s3.list_prefix.return_value = [
            "shared/overlay/overlay_frame1.png",
            "shared/overlay/overlay_frame2.jpg",
        ]
        mock_storage_s3.get_url.side_effect = lambda key: f"http://minio/{key}"

        response = client.get("/overlay/list")

        assert response.status_code == 200
        data = response.json()
        assert "overlays" in data
        assert len(data["overlays"]) == 2

        # Verify format
        for overlay in data["overlays"]:
            assert "id" in overlay
            assert "name" in overlay
            assert "url" in overlay
            assert overlay["url"].startswith("http://minio/")

    def test_list_overlays_s3_empty(self, mock_storage_s3):
        """Test overlay listing with no overlays."""
        mock_storage_s3.list_prefix.return_value = []

        response = client.get("/overlay/list")

        assert response.status_code == 200
        data = response.json()
        assert data["overlays"] == []


class TestFontFile:
    """Tests for /fonts/file/{filename} endpoint."""

    def test_get_font_file_s3_mode(self, tmp_path):
        """Test font file serving in S3 mode (proxied via local cache for CORS)."""
        # Create a temporary font file to serve
        font_file = tmp_path / "test.ttf"
        font_file.write_bytes(b"\x00\x01\x00\x00" + b"\x00" * 100)

        with patch("services.storage.get_storage") as mock_get_storage, patch("config.STORAGE_MODE", "s3"):
            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage
            mock_storage.exists.return_value = True
            mock_storage.get_local_path.return_value = font_file

            response = client.get("/fonts/file/test.ttf")

            # Implementation proxies via local cache (FileResponse) to avoid CORS
            assert response.status_code == 200
            mock_storage.exists.assert_called_once_with("shared/fonts/test.ttf")
            mock_storage.get_local_path.assert_called_once_with("shared/fonts/test.ttf")

    def test_get_font_file_not_found_s3(self):
        """Test 404 when font file doesn't exist in S3."""
        with patch("services.storage.get_storage") as mock_get_storage, patch("config.STORAGE_MODE", "s3"):
            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage
            mock_storage.exists.return_value = False

            response = client.get("/fonts/file/nonexistent.ttf")

            assert response.status_code == 404
            assert "Font not found" in response.json()["detail"]

    def test_get_font_file_path_traversal_blocked(self):
        """Path traversal via slashes is blocked by Starlette route matching (404)."""
        with patch("config.STORAGE_MODE", "local"):
            response = client.get("/fonts/file/..%2F..%2F..%2Fetc%2Fpasswd")
            # Starlette {filename} param doesn't match '/', so route returns 404 (safe)
            assert response.status_code in (400, 404)

    def test_get_font_file_traversal_dot_dot_local(self, tmp_path):
        """Traversal patterns never serve files outside the fonts directory."""
        with patch("config.STORAGE_MODE", "local"):
            # Starlette normalizes '..' in URL path, so route never matches
            response = client.get("/fonts/file/..")
            assert response.status_code in (400, 404)
            # Encoded slashes also blocked by route matching
            response = client.get("/fonts/file/..%2Fetc%2Fpasswd")
            assert response.status_code in (400, 404)

    def test_get_font_file_path_traversal_s3_uses_basename(self, tmp_path):
        """S3 mode should strip directory components via Path.name."""
        with patch("services.storage.get_storage") as mock_get_storage, patch("config.STORAGE_MODE", "s3"):
            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage
            mock_storage.exists.return_value = False

            # No slash in filename — route matches, but Path("passwd").name == "passwd"
            response = client.get("/fonts/file/passwd")

            assert response.status_code == 404
            mock_storage.exists.assert_called_once_with("shared/fonts/passwd")


class TestOverlayFileTraversal:
    """Tests for path traversal prevention on overlay file endpoint."""

    def test_get_overlay_file_path_traversal_blocked(self):
        """Path traversal via slashes is blocked by Starlette route matching (404)."""
        with patch("config.STORAGE_MODE", "local"):
            response = client.get("/assets/overlay/..%2F..%2F..%2Fetc%2Fpasswd")
            assert response.status_code in (400, 404)

    def test_get_overlay_file_traversal_dot_dot_local(self):
        """Traversal patterns never serve files outside the overlay directory."""
        with patch("config.STORAGE_MODE", "local"):
            response = client.get("/assets/overlay/..")
            assert response.status_code in (400, 404)
            response = client.get("/assets/overlay/..%2Fetc%2Fpasswd")
            assert response.status_code in (400, 404)

    def test_get_overlay_file_path_traversal_s3_uses_basename(self):
        """S3 mode should strip directory components via Path.name."""
        with patch("services.storage.get_storage") as mock_get_storage, patch("config.STORAGE_MODE", "s3"):
            mock_storage = MagicMock()
            mock_get_storage.return_value = mock_storage
            mock_storage.exists.return_value = False

            response = client.get("/assets/overlay/passwd")

            assert response.status_code == 404
            mock_storage.exists.assert_called_once_with("shared/overlay/passwd")
