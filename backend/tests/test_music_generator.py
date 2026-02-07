"""Unit tests for music_generator service (cache key, generation mock)."""

from unittest.mock import MagicMock, patch

from services.audio.music_generator import _music_cache_key


class TestMusicCacheKey:
    """Tests for _music_cache_key determinism."""

    def test_same_inputs_same_key(self):
        k1 = _music_cache_key("lo-fi chill", 30.0, 42, 100)
        k2 = _music_cache_key("lo-fi chill", 30.0, 42, 100)
        assert k1 == k2

    def test_different_prompt_different_key(self):
        k1 = _music_cache_key("lo-fi chill", 30.0, 42, 100)
        k2 = _music_cache_key("epic orchestra", 30.0, 42, 100)
        assert k1 != k2

    def test_different_duration_different_key(self):
        k1 = _music_cache_key("lo-fi chill", 30.0, 42, 100)
        k2 = _music_cache_key("lo-fi chill", 20.0, 42, 100)
        assert k1 != k2

    def test_different_seed_different_key(self):
        k1 = _music_cache_key("lo-fi chill", 30.0, 42, 100)
        k2 = _music_cache_key("lo-fi chill", 30.0, 99, 100)
        assert k1 != k2

    def test_different_steps_different_key(self):
        k1 = _music_cache_key("lo-fi chill", 30.0, 42, 100)
        k2 = _music_cache_key("lo-fi chill", 30.0, 42, 50)
        assert k1 != k2

    def test_key_length_is_16(self):
        key = _music_cache_key("test", 10.0, 1, 100)
        assert len(key) == 16


class TestGenerateMusicCacheHit:
    """Test generate_music returns cached bytes when cache file exists."""

    @patch("services.audio.music_generator._cache_path")
    def test_cache_hit_returns_bytes(self, mock_cache_path):
        cached = MagicMock()
        cached.exists.return_value = True
        cached.read_bytes.return_value = b"RIFF_fake_wav"
        mock_cache_path.return_value = cached

        from services.audio.music_generator import generate_music

        with patch("services.audio.music_generator.get_sao_model_sync") as mock_model:
            wav_bytes, sr, seed = generate_music("test", duration=10.0, seed=42)

        assert wav_bytes == b"RIFF_fake_wav"
        assert sr == 44100
        assert seed == 42
        mock_model.assert_not_called()

    @patch("services.audio.music_generator._cache_path")
    def test_negative_seed_becomes_positive(self, mock_cache_path):
        """Negative seed should be replaced with a random positive seed."""
        cached = MagicMock()
        cached.exists.return_value = True
        cached.read_bytes.return_value = b"wav"
        mock_cache_path.return_value = cached

        from services.audio.music_generator import generate_music

        _, _, actual_seed = generate_music("prompt", seed=-1)
        assert actual_seed >= 0
