"""Tests for load_as_data_url helper in services/image.py."""

import base64
from unittest.mock import patch

import pytest

from services.image import load_as_data_url


class TestLoadAsDataUrl:
    """Test load_as_data_url() returns correct data URL format."""

    def test_from_data_url(self):
        """Data URL input is re-encoded as data URL output."""
        original_bytes = b"test-image-bytes"
        source = f"data:image/png;base64,{base64.b64encode(original_bytes).decode()}"

        result = load_as_data_url(source)

        assert result.startswith("data:image/png;base64,")
        decoded = base64.b64decode(result.split(",", 1)[1])
        assert decoded == original_bytes

    def test_from_raw_base64(self):
        """Raw base64 string is converted to data URL."""
        original_bytes = b"raw-b64-content"
        source = base64.b64encode(original_bytes).decode()

        result = load_as_data_url(source)

        assert result.startswith("data:image/png;base64,")
        decoded = base64.b64decode(result.split(",", 1)[1])
        assert decoded == original_bytes

    def test_empty_source_raises(self):
        """Empty source raises ValueError."""
        with pytest.raises(ValueError, match="Empty image data"):
            load_as_data_url("")

    def test_from_storage_url(self):
        """Storage URL is loaded via load_image_bytes and converted."""
        fake_bytes = b"storage-image-content"

        with patch("services.image.load_image_bytes", return_value=fake_bytes) as mock_load:
            result = load_as_data_url("http://localhost:9000/bucket/key.png")

        mock_load.assert_called_once_with("http://localhost:9000/bucket/key.png")
        decoded = base64.b64decode(result.split(",", 1)[1])
        assert decoded == fake_bytes
