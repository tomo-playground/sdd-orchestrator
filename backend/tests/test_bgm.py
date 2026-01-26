"""Unit tests for BGM random selection."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.video import resolve_bgm_file


class TestResolveBgmFile:
    """Tests for resolve_bgm_file function."""

    def test_none_returns_none(self):
        """None bgm_file should return None."""
        result = resolve_bgm_file(None, Path("/fake/audio"))
        assert result is None

    def test_empty_string_returns_none(self):
        """Empty string should return None."""
        result = resolve_bgm_file("", Path("/fake/audio"))
        assert result is None

    def test_specific_file_returns_same(self):
        """Specific filename should be returned as-is."""
        result = resolve_bgm_file("my_bgm.mp3", Path("/fake/audio"))
        assert result == "my_bgm.mp3"

    def test_random_selects_from_directory(self, tmp_path):
        """'random' should select a random mp3 from directory."""
        # Create fake audio files
        (tmp_path / "bgm1.mp3").touch()
        (tmp_path / "bgm2.mp3").touch()
        (tmp_path / "bgm3.mp3").touch()
        (tmp_path / "not_audio.txt").touch()  # Should be ignored

        result = resolve_bgm_file("random", tmp_path)

        assert result in ["bgm1.mp3", "bgm2.mp3", "bgm3.mp3"]

    def test_random_empty_directory_returns_none(self, tmp_path):
        """'random' with no mp3 files should return None."""
        (tmp_path / "not_audio.txt").touch()

        result = resolve_bgm_file("random", tmp_path)

        assert result is None

    def test_random_nonexistent_directory_returns_none(self):
        """'random' with non-existent directory should return None."""
        result = resolve_bgm_file("random", Path("/nonexistent/path"))
        assert result is None

    def test_random_seed_reproducibility(self, tmp_path):
        """Same seed should return same random selection."""
        (tmp_path / "bgm1.mp3").touch()
        (tmp_path / "bgm2.mp3").touch()
        (tmp_path / "bgm3.mp3").touch()

        result1 = resolve_bgm_file("random", tmp_path, seed=12345)
        result2 = resolve_bgm_file("random", tmp_path, seed=12345)

        assert result1 == result2

    def test_random_different_seeds_may_differ(self, tmp_path):
        """Different seeds should (likely) produce different results."""
        for i in range(10):
            (tmp_path / f"bgm{i}.mp3").touch()

        results = set()
        for seed in range(50):
            result = resolve_bgm_file("random", tmp_path, seed=seed)
            results.add(result)

        # Should have multiple different selections
        assert len(results) > 1

    def test_random_case_insensitive(self, tmp_path):
        """'RANDOM' and 'Random' should also work."""
        (tmp_path / "bgm1.mp3").touch()

        assert resolve_bgm_file("RANDOM", tmp_path) == "bgm1.mp3"
        assert resolve_bgm_file("Random", tmp_path) == "bgm1.mp3"
