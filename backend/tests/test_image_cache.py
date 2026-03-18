"""Tests for Image Generation Cache service.

Covers:
- Cache key determinism
- Seed/ControlNet diff → different keys
- Disabled mode behavior
- Save + get round-trip
- Eviction logic
- Clear operation
- Stats reporting
"""

from __future__ import annotations

from unittest.mock import patch


class TestImageCacheKey:
    """Test cache key generation."""

    def test_same_payload_same_key(self):
        """Identical payloads produce identical keys."""
        from services.image_cache import image_cache_key

        payload = {
            "prompt": "1girl, masterpiece",
            "negative_prompt": "lowres",
            "seed": 42,
            "width": 832,
            "height": 1216,
            "steps": 28,
            "cfg_scale": 4.5,
            "sampler_name": "Euler",
            "override_settings": {"CLIP_stop_at_last_layers": 2},
        }
        k1 = image_cache_key(payload)
        k2 = image_cache_key(payload)
        assert k1 == k2
        assert len(k1) == 16

    def test_different_seed_different_key(self):
        """Different seeds → different keys."""
        from services.image_cache import image_cache_key

        base = {"prompt": "test", "seed": 42}
        k1 = image_cache_key(base)
        k2 = image_cache_key({**base, "seed": 43})
        assert k1 != k2

    def test_different_prompt_different_key(self):
        """Different prompts → different keys."""
        from services.image_cache import image_cache_key

        k1 = image_cache_key({"prompt": "a", "seed": 42})
        k2 = image_cache_key({"prompt": "b", "seed": 42})
        assert k1 != k2

    def test_controlnet_affects_key(self):
        """ControlNet args should be included in cache key."""
        from services.image_cache import image_cache_key

        base = {"prompt": "test", "seed": 42}
        with_cn = {
            **base,
            "alwayson_scripts": {
                "controlnet": {
                    "args": [{"model": "openpose", "weight": 1.0}],
                },
            },
        }
        k1 = image_cache_key(base)
        k2 = image_cache_key(with_cn)
        assert k1 != k2


class TestImageCacheDisabled:
    """Test behavior when cache is disabled."""

    def test_get_returns_none_when_disabled(self):
        """get_cached_image returns None when disabled."""
        from services.image_cache import get_cached_image

        with patch("services.image_cache.SD_IMAGE_CACHE_ENABLED", False):
            result = get_cached_image("some_key")
        assert result is None

    def test_save_is_noop_when_disabled(self):
        """save_cached_image does nothing when disabled."""
        from services.image_cache import save_cached_image

        with patch("services.image_cache.SD_IMAGE_CACHE_ENABLED", False):
            # Should not raise
            save_cached_image("some_key", "base64data")


class TestImageCacheRoundTrip:
    """Test save → get round-trip."""

    def test_save_and_retrieve(self, tmp_path):
        """Saved image can be retrieved by same key."""
        from services.image_cache import get_cached_image, save_cached_image

        with (
            patch("services.image_cache.SD_IMAGE_CACHE_ENABLED", True),
            patch("services.image_cache._CACHE_DIR", tmp_path),
        ):
            save_cached_image("testkey1", "iVBORw0KGgo=")
            result = get_cached_image("testkey1")
            assert result == "iVBORw0KGgo="

    def test_missing_key_returns_none(self, tmp_path):
        """Non-existent key returns None."""
        from services.image_cache import get_cached_image

        with (
            patch("services.image_cache.SD_IMAGE_CACHE_ENABLED", True),
            patch("services.image_cache._CACHE_DIR", tmp_path),
        ):
            result = get_cached_image("nonexistent")
            assert result is None


class TestImageCacheEviction:
    """Test LRU eviction."""

    def test_evicts_oldest_when_over_limit(self, tmp_path):
        """When cache exceeds max size, oldest files are evicted."""
        from services.image_cache import clear_image_cache, save_cached_image

        # Create large data to trigger eviction with tiny limit
        data = "A" * 1024  # 1KB each

        with (
            patch("services.image_cache.SD_IMAGE_CACHE_ENABLED", True),
            patch("services.image_cache._CACHE_DIR", tmp_path),
            patch("services.image_cache.SD_IMAGE_CACHE_MAX_SIZE_MB", 0),  # 0 MB = always evict
        ):
            save_cached_image("file1", data)
            save_cached_image("file2", data)
            save_cached_image("file3", data)

            # With 0MB limit, files get evicted after each save
            # Verify eviction ran (fewer files than 3 should remain)
            remaining = list(tmp_path.glob("*.b64"))
            # At most 1 file can survive (the last one saved, then evicted by its own save)
            assert len(remaining) <= 1


class TestImageCacheClear:
    """Test cache clear."""

    def test_clear_removes_all(self, tmp_path):
        """clear_image_cache removes all .b64 files."""
        from services.image_cache import clear_image_cache, save_cached_image

        with (
            patch("services.image_cache.SD_IMAGE_CACHE_ENABLED", True),
            patch("services.image_cache._CACHE_DIR", tmp_path),
        ):
            save_cached_image("a", "data1")
            save_cached_image("b", "data2")
            count = clear_image_cache()
            assert count == 2
            assert len(list(tmp_path.glob("*.b64"))) == 0


class TestImageCacheStats:
    """Test stats reporting."""

    def test_stats_structure(self, tmp_path):
        """get_cache_stats returns expected fields."""
        from services.image_cache import get_cache_stats

        with patch("services.image_cache._CACHE_DIR", tmp_path):
            stats = get_cache_stats()
            assert "enabled" in stats
            assert "file_count" in stats
            assert "total_size_mb" in stats
            assert "max_size_mb" in stats
            assert stats["file_count"] == 0
