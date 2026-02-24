"""Tests for tag thumbnail service (Phase 15-B)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ------------------------------------------------------------------
# Danbooru get_post_image
# ------------------------------------------------------------------


class TestGetPostImage:
    """Tests for danbooru.get_post_image()."""

    @pytest.mark.asyncio
    async def test_returns_preview_url_on_success(self):
        from services.danbooru import get_post_image

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {"id": 123, "preview_file_url": "https://cdn.donmai.us/preview/abc.jpg"}
        ]

        with patch("services.danbooru.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await get_post_image("smile")

        assert result is not None
        assert result["preview_url"] == "https://cdn.donmai.us/preview/abc.jpg"
        assert result["post_id"] == 123

    @pytest.mark.asyncio
    async def test_returns_none_when_no_posts(self):
        from services.danbooru import get_post_image

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = []

        with patch("services.danbooru.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await get_post_image("nonexistent_tag_xyz")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_network_error(self):
        import httpx

        from services.danbooru import get_post_image

        with patch("services.danbooru.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectTimeout("timeout"))
            mock_client_cls.return_value = mock_client

            result = await get_post_image("smile")

        assert result is None


# ------------------------------------------------------------------
# Thumbnail resize helper
# ------------------------------------------------------------------


class TestResizeToWebp:
    """Tests for _resize_to_webp helper."""

    def test_resizes_valid_image(self):
        from PIL import Image as PILImage

        from services.tag_thumbnail import _resize_to_webp

        # Create a small test image
        img = PILImage.new("RGB", (300, 300), color="red")
        import io

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        result = _resize_to_webp(png_bytes)
        assert result is not None
        assert len(result) > 0
        # Verify it's valid WebP
        result_img = PILImage.open(io.BytesIO(result))
        assert result_img.format == "WEBP"
        assert max(result_img.size) <= 150  # TAG_THUMBNAIL_WIDTH default

    def test_returns_none_for_invalid_data(self):
        from services.tag_thumbnail import _resize_to_webp

        result = _resize_to_webp(b"not an image")
        assert result is None


# ------------------------------------------------------------------
# fetch_and_save_thumbnail
# ------------------------------------------------------------------


class TestFetchAndSaveThumbnail:
    """Tests for fetch_and_save_thumbnail."""

    def test_skips_if_already_has_thumbnail(self):
        from services.tag_thumbnail import fetch_and_save_thumbnail

        tag = MagicMock()
        tag.thumbnail_asset_id = 42
        db = MagicMock()

        result = fetch_and_save_thumbnail(tag, db)
        assert result is True

    @patch("services.tag_thumbnail.get_post_image")
    @patch("services.tag_thumbnail.asyncio.run")
    def test_returns_false_when_no_image_found(self, mock_run, mock_get_post):
        from services.tag_thumbnail import fetch_and_save_thumbnail

        mock_run.return_value = None

        tag = MagicMock()
        tag.thumbnail_asset_id = None
        tag.name = "obscure_tag"
        db = MagicMock()

        result = fetch_and_save_thumbnail(tag, db)
        assert result is False

    @patch("services.tag_thumbnail._resize_to_webp")
    @patch("services.tag_thumbnail._download_image")
    @patch("services.tag_thumbnail.asyncio.run")
    def test_saves_thumbnail_on_success(self, mock_run, mock_download, mock_resize):
        from services.tag_thumbnail import fetch_and_save_thumbnail

        mock_run.return_value = {"preview_url": "https://example.com/img.jpg", "post_id": 1}
        mock_download.return_value = b"fake_image_bytes"
        mock_resize.return_value = b"fake_webp_bytes"

        tag = MagicMock()
        tag.thumbnail_asset_id = None
        tag.id = 10
        tag.name = "smile"
        db = MagicMock()

        mock_asset = MagicMock()
        mock_asset.id = 99

        with patch("services.tag_thumbnail.AssetService") as mock_asset_svc_cls:
            mock_svc = MagicMock()
            mock_svc.register_asset.return_value = mock_asset
            mock_asset_svc_cls.return_value = mock_svc

            result = fetch_and_save_thumbnail(tag, db)

        assert result is True
        assert tag.thumbnail_asset_id == 99
        db.commit.assert_called()


# ------------------------------------------------------------------
# generate_batch_thumbnails
# ------------------------------------------------------------------


class TestGenerateBatchThumbnails:
    """Tests for generate_batch_thumbnails."""

    @patch("services.tag_thumbnail.fetch_and_save_thumbnail")
    def test_processes_tags_in_group(self, mock_fetch):
        from services.tag_thumbnail import generate_batch_thumbnails

        mock_fetch.return_value = True

        tag1 = MagicMock(name="smile", thumbnail_asset_id=None, is_active=True)
        tag2 = MagicMock(name="crying", thumbnail_asset_id=None, is_active=True)

        db = MagicMock()
        mock_query = MagicMock()
        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [tag1, tag2]

        with patch("services.tag_thumbnail.TAG_THUMBNAIL_BATCH_DELAY_MS", 0):
            result = generate_batch_thumbnails(db, group_name="expression")

        assert result["total"] == 2
        assert result["succeeded"] == 2
        assert result["failed"] == 0

    @patch("services.tag_thumbnail.fetch_and_save_thumbnail")
    def test_counts_failures(self, mock_fetch):
        from services.tag_thumbnail import generate_batch_thumbnails

        mock_fetch.side_effect = [True, False]

        tag1 = MagicMock(name="smile", thumbnail_asset_id=None)
        tag2 = MagicMock(name="obscure", thumbnail_asset_id=None)

        db = MagicMock()
        mock_query = MagicMock()
        db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [tag1, tag2]

        with patch("services.tag_thumbnail.TAG_THUMBNAIL_BATCH_DELAY_MS", 0):
            result = generate_batch_thumbnails(db, group_name="expression")

        assert result["total"] == 2
        assert result["succeeded"] == 1
        assert result["failed"] == 1
