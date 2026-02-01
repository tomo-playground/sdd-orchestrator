"""Test image storage key extraction and normalization."""
import pytest

from services.validation import _extract_storage_key


class TestExtractStorageKey:
    """Test _extract_storage_key helper function."""

    def test_already_storage_key(self):
        """Storage key passes through unchanged."""
        key = "projects/1/groups/1/storyboards/1/images/scene_123.png"
        assert _extract_storage_key(key) == key

    def test_shared_storage_key(self):
        """Shared storage key passes through unchanged."""
        key = "shared/characters/char_123.png"
        assert _extract_storage_key(key) == key

    def test_minio_url_full(self):
        """Extract from full MinIO URL."""
        url = "http://localhost:9000/shorts-producer/projects/1/groups/1/storyboards/1/images/scene_123.png"
        expected = "projects/1/groups/1/storyboards/1/images/scene_123.png"
        assert _extract_storage_key(url) == expected

    def test_minio_url_https(self):
        """Extract from HTTPS MinIO URL."""
        url = "https://minio.example.com/shorts-producer/projects/2/groups/3/storyboards/4/images/scene_456.png"
        expected = "projects/2/groups/3/storyboards/4/images/scene_456.png"
        assert _extract_storage_key(url) == expected

    def test_bucket_url_pattern(self):
        """Extract from bucket URL pattern (without shorts-producer prefix)."""
        url = "http://localhost:9000/bucket/projects/1/groups/1/storyboards/1/images/scene_789.png"
        expected = "projects/1/groups/1/storyboards/1/images/scene_789.png"
        assert _extract_storage_key(url) == expected

    def test_absolute_path_outputs(self):
        """Absolute path returns None (irrecoverable)."""
        path = "/outputs/images/scene_123.png"
        assert _extract_storage_key(path) is None

    def test_absolute_path_tmp(self):
        """Temporary absolute path returns None."""
        path = "/tmp/scene_456.png"
        assert _extract_storage_key(path) is None

    def test_none_input(self):
        """None input returns None."""
        assert _extract_storage_key(None) is None

    def test_empty_string(self):
        """Empty string returns None."""
        assert _extract_storage_key("") is None

    def test_unknown_format(self):
        """Unknown format returns None and logs warning."""
        weird_url = "ftp://example.com/image.png"
        assert _extract_storage_key(weird_url) is None

    def test_shared_minio_url(self):
        """Extract shared storage key from MinIO URL."""
        url = "http://localhost:9000/shorts-producer/shared/characters/char_123.png"
        expected = "shared/characters/char_123.png"
        assert _extract_storage_key(url) == expected
