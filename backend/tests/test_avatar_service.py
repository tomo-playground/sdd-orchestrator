"""Tests for avatar service functions."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

PATCH_PREFIX = "services.avatar"


class TestAvatarFilename:
    """Test avatar_filename utility."""

    def test_generates_consistent_hash(self):
        """Same input produces same output."""
        from services.avatar import avatar_filename

        result1 = avatar_filename("test_channel")
        result2 = avatar_filename("test_channel")
        assert result1 == result2
        assert result1.startswith("avatar_")
        assert result1.endswith(".png")

    def test_different_inputs_produce_different_hashes(self):
        """Different inputs produce different hashes."""
        from services.avatar import avatar_filename

        result1 = avatar_filename("channel_a")
        result2 = avatar_filename("channel_b")
        assert result1 != result2

    def test_handles_empty_string(self):
        """Empty string defaults to 'avatar'."""
        from services.avatar import avatar_filename

        result = avatar_filename("")
        assert result.startswith("avatar_")

    def test_handles_url_input(self):
        """URL input is hashed consistently."""
        from services.avatar import avatar_filename

        url = "http://localhost:9000/shorts-producer/characters/9/preview.png"
        result1 = avatar_filename(url)
        result2 = avatar_filename(url)
        assert result1 == result2
        assert result1.startswith("avatar_")


class TestDownloadAvatarFromUrl:
    """Test _download_avatar_from_url function."""

    @pytest.mark.asyncio
    @patch(f"{PATCH_PREFIX}.get_storage")
    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    async def test_downloads_and_saves_image(self, mock_client_cls, mock_storage_fn):
        """Successfully download and save avatar from URL."""
        from services.avatar import _download_avatar_from_url

        # Mock storage
        mock_storage = MagicMock()
        mock_storage.exists.return_value = False
        mock_storage_fn.return_value = mock_storage

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"x" * 1000  # Fake image bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        url = "http://localhost:9000/test/avatar.png"
        result = await _download_avatar_from_url(url)

        assert result is not None
        assert result.startswith("shared/avatars/")
        mock_storage.save.assert_called_once()

    @pytest.mark.asyncio
    @patch(f"{PATCH_PREFIX}.get_storage")
    async def test_returns_cached_if_exists(self, mock_storage_fn):
        """Return cached avatar if it already exists."""
        from services.avatar import _download_avatar_from_url

        mock_storage = MagicMock()
        mock_storage.exists.return_value = True
        mock_storage_fn.return_value = mock_storage

        url = "http://localhost:9000/test/avatar.png"
        result = await _download_avatar_from_url(url)

        assert result is not None
        assert result.startswith("shared/avatars/")
        mock_storage.save.assert_not_called()

    @pytest.mark.asyncio
    @patch(f"{PATCH_PREFIX}.get_storage")
    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    async def test_returns_none_on_download_failure(self, mock_client_cls, mock_storage_fn):
        """Return None when download fails."""
        from services.avatar import _download_avatar_from_url

        mock_storage = MagicMock()
        mock_storage.exists.return_value = False
        mock_storage_fn.return_value = mock_storage

        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection failed")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        url = "http://localhost:9000/test/avatar.png"
        result = await _download_avatar_from_url(url)

        assert result is None

    @pytest.mark.asyncio
    @patch(f"{PATCH_PREFIX}.get_storage")
    @patch(f"{PATCH_PREFIX}.httpx.AsyncClient")
    async def test_returns_none_for_small_response(self, mock_client_cls, mock_storage_fn):
        """Return None when downloaded content is too small."""
        from services.avatar import _download_avatar_from_url

        mock_storage = MagicMock()
        mock_storage.exists.return_value = False
        mock_storage_fn.return_value = mock_storage

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"tiny"  # Too small (< 100 bytes)
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        url = "http://localhost:9000/test/avatar.png"
        result = await _download_avatar_from_url(url)

        assert result is None
        mock_storage.save.assert_not_called()


class TestEnsureAvatarFile:
    """Test ensure_avatar_file function."""

    @pytest.mark.asyncio
    @patch(f"{PATCH_PREFIX}._download_avatar_from_url", new_callable=AsyncMock)
    async def test_delegates_to_download_for_http_url(self, mock_download):
        """HTTP URLs are delegated to _download_avatar_from_url."""
        from services.avatar import ensure_avatar_file

        mock_download.return_value = "shared/avatars/avatar_abc.png"

        url = "http://localhost:9000/test/avatar.png"
        result = await ensure_avatar_file(url)

        assert result == "shared/avatars/avatar_abc.png"
        mock_download.assert_called_once_with(url, 60.0)

    @pytest.mark.asyncio
    @patch(f"{PATCH_PREFIX}._download_avatar_from_url", new_callable=AsyncMock)
    async def test_delegates_to_download_for_https_url(self, mock_download):
        """HTTPS URLs are delegated to _download_avatar_from_url."""
        from services.avatar import ensure_avatar_file

        mock_download.return_value = "shared/avatars/avatar_xyz.png"

        url = "https://example.com/avatar.png"
        result = await ensure_avatar_file(url)

        assert result == "shared/avatars/avatar_xyz.png"
        mock_download.assert_called_once_with(url, 60.0)

    @pytest.mark.asyncio
    @patch(f"{PATCH_PREFIX}.get_storage")
    async def test_returns_cached_for_non_url_key(self, mock_storage_fn):
        """Non-URL keys check cache first."""
        from services.avatar import ensure_avatar_file

        mock_storage = MagicMock()
        mock_storage.exists.return_value = True
        mock_storage_fn.return_value = mock_storage

        result = await ensure_avatar_file("my_channel")

        assert result is not None
        assert result.startswith("shared/avatars/")
