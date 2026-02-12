"""Test upload validation: MIME whitelist, size limit, magic bytes."""

from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi import HTTPException, UploadFile

from services.upload_validation import validate_image_upload

# Minimal valid PNG header (8 bytes)
PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
# Minimal valid JPEG header
JPEG_HEADER = b"\xff\xd8\xff\xe0" + b"\x00" * 100
# Minimal valid GIF header
GIF_HEADER = b"GIF89a" + b"\x00" * 100
# Minimal valid WEBP header
WEBP_HEADER = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100


def _make_upload(data: bytes, content_type: str, filename: str = "test.png") -> UploadFile:
    """Create an UploadFile from raw bytes."""
    return UploadFile(file=BytesIO(data), filename=filename, headers={"content-type": content_type})


class TestValidateMime:
    @pytest.mark.asyncio
    async def test_valid_png(self):
        file = _make_upload(PNG_HEADER, "image/png")
        result = await validate_image_upload(file)
        assert result == PNG_HEADER

    @pytest.mark.asyncio
    async def test_valid_jpeg(self):
        file = _make_upload(JPEG_HEADER, "image/jpeg")
        result = await validate_image_upload(file)
        assert result == JPEG_HEADER

    @pytest.mark.asyncio
    async def test_valid_gif(self):
        file = _make_upload(GIF_HEADER, "image/gif")
        result = await validate_image_upload(file)
        assert result == GIF_HEADER

    @pytest.mark.asyncio
    async def test_valid_webp(self):
        file = _make_upload(WEBP_HEADER, "image/webp")
        result = await validate_image_upload(file)
        assert result == WEBP_HEADER

    @pytest.mark.asyncio
    async def test_reject_invalid_mime(self):
        file = _make_upload(b"PK\x03\x04", "application/zip")
        with pytest.raises(HTTPException) as exc_info:
            await validate_image_upload(file)
        assert exc_info.value.status_code == 400
        assert "허용되지 않는" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_reject_empty_mime(self):
        file = _make_upload(b"data", "")
        with pytest.raises(HTTPException) as exc_info:
            await validate_image_upload(file)
        assert exc_info.value.status_code == 400


class TestValidateSize:
    @pytest.mark.asyncio
    async def test_reject_oversized_file(self):
        # Create data slightly over limit
        with patch("services.upload_validation.MAX_IMAGE_UPLOAD_BYTES", 1024):
            file = _make_upload(PNG_HEADER + b"\x00" * 1024, "image/png")
            with pytest.raises(HTTPException) as exc_info:
                await validate_image_upload(file)
            assert exc_info.value.status_code == 400
            assert "제한을 초과" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_accept_within_limit(self):
        with patch("services.upload_validation.MAX_IMAGE_UPLOAD_BYTES", 10240):
            file = _make_upload(PNG_HEADER, "image/png")
            result = await validate_image_upload(file)
            assert len(result) > 0


class TestValidateMagicBytes:
    @pytest.mark.asyncio
    async def test_reject_magic_mismatch(self):
        """PNG MIME but JPEG magic bytes should fail."""
        file = _make_upload(JPEG_HEADER, "image/png")
        with pytest.raises(HTTPException) as exc_info:
            await validate_image_upload(file)
        assert exc_info.value.status_code == 400
        assert "일치하지 않습니다" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_reject_random_data_as_png(self):
        """Random data with PNG MIME should fail magic check."""
        file = _make_upload(b"random_data_here_not_png", "image/png")
        with pytest.raises(HTTPException) as exc_info:
            await validate_image_upload(file)
        assert exc_info.value.status_code == 400
