"""Unit tests for BGM random selection."""

from unittest.mock import patch

from services.video import resolve_bgm_file


class TestResolveBgmFile:
    """Tests for resolve_bgm_file function."""

    def test_none_returns_none(self):
        """None bgm_file should return None."""
        result = resolve_bgm_file(None)
        assert result is None

    def test_empty_string_returns_none(self):
        """Empty string should return None."""
        result = resolve_bgm_file("")
        assert result is None

    def test_specific_file_returns_same(self):
        """Specific filename should be returned as-is."""
        result = resolve_bgm_file("my_bgm.mp3")
        assert result == "my_bgm.mp3"

    @patch("services.video.get_storage")
    def test_random_selects_from_directory(self, mock_get_storage):
        """'random' should select a random mp3 from storage."""
        mock_storage = mock_get_storage.return_value
        mock_storage.list_prefix.return_value = [
            "shared/audio/bgm1.mp3",
            "shared/audio/bgm2.mp3",
            "shared/audio/bgm3.mp3",
        ]

        result = resolve_bgm_file("random")

        assert result in ["bgm1.mp3", "bgm2.mp3", "bgm3.mp3"]

    @patch("services.video.get_storage")
    def test_random_empty_directory_returns_none(self, mock_get_storage):
        """'random' with no mp3 files should return None."""
        mock_storage = mock_get_storage.return_value
        mock_storage.list_prefix.return_value = ["shared/audio/not_audio.txt"]

        result = resolve_bgm_file("random")

        assert result is None

    @patch("services.video.get_storage")
    def test_random_nonexistent_directory_returns_none(self, mock_get_storage):
        """'random' with empty storage should return None."""
        mock_storage = mock_get_storage.return_value
        mock_storage.list_prefix.return_value = []

        result = resolve_bgm_file("random")
        assert result is None

    @patch("services.video.get_storage")
    def test_random_seed_reproducibility(self, mock_get_storage):
        """Same seed should return same random selection."""
        mock_storage = mock_get_storage.return_value
        mock_storage.list_prefix.return_value = [
            "shared/audio/bgm1.mp3",
            "shared/audio/bgm2.mp3",
            "shared/audio/bgm3.mp3",
        ]

        result1 = resolve_bgm_file("random", seed=12345)
        result2 = resolve_bgm_file("random", seed=12345)

        assert result1 == result2

    @patch("services.video.get_storage")
    def test_random_different_seeds_may_differ(self, mock_get_storage):
        """Different seeds should (likely) produce different results."""
        keys = [f"shared/audio/bgm{i}.mp3" for i in range(10)]
        mock_storage = mock_get_storage.return_value
        mock_storage.list_prefix.return_value = keys

        results = set()
        for seed in range(50):
            result = resolve_bgm_file("random", seed=seed)
            results.add(result)

        # Should have multiple different selections
        assert len(results) > 1

    @patch("services.video.get_storage")
    def test_random_case_insensitive(self, mock_get_storage):
        """'RANDOM' and 'Random' should also work."""
        mock_storage = mock_get_storage.return_value
        mock_storage.list_prefix.return_value = ["shared/audio/bgm1.mp3"]

        assert resolve_bgm_file("RANDOM") == "bgm1.mp3"
        assert resolve_bgm_file("Random") == "bgm1.mp3"
