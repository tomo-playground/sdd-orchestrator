"""Unit tests for apply_bgm manual/auto modes in effects module."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.video.effects import _resolve_bgm_path


class TestResolveBgmPath:
    """Tests for _resolve_bgm_path with manual and auto modes."""

    def test_manual_mode_returns_ai_bgm_path(self):
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="manual")
        builder._ai_bgm_path = "/tmp/ai_bgm.wav"

        result = _resolve_bgm_path(builder)
        assert result == "/tmp/ai_bgm.wav"

    def test_manual_mode_returns_none_when_no_path_and_no_file(self):
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="manual", bgm_file=None)
        builder._ai_bgm_path = None
        builder.project_id = "build_123"

        with patch("services.video.effects.resolve_bgm_file", return_value=None):
            result = _resolve_bgm_path(builder)
        assert result is None

    @patch("services.video.effects.get_storage")
    @patch("services.video.effects.resolve_bgm_file")
    def test_manual_mode_falls_back_to_bgm_file(self, mock_resolve, mock_storage):
        """Manual mode with no preset path should fall back to bgm_file."""
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="manual", bgm_file="song.mp3")
        builder._ai_bgm_path = None
        builder.project_id = "build_123"
        mock_resolve.return_value = "song.mp3"

        storage = mock_storage.return_value
        storage.exists.return_value = True
        storage.get_local_path.return_value = "/data/shared/audio/song.mp3"

        result = _resolve_bgm_path(builder)
        assert result == "/data/shared/audio/song.mp3"
        mock_resolve.assert_called_once()

    @patch("services.video.effects.get_storage")
    @patch("services.video.effects.resolve_bgm_file")
    def test_manual_mode_preset_takes_priority_over_file(self, mock_resolve, _mock_storage):
        """Manual mode with preset path should NOT fall back to bgm_file."""
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="manual", bgm_file="song.mp3")
        builder._ai_bgm_path = "/tmp/preset_bgm.wav"
        builder.project_id = "build_123"

        result = _resolve_bgm_path(builder)
        assert result == "/tmp/preset_bgm.wav"
        mock_resolve.assert_not_called()

    def test_legacy_file_mode_maps_to_manual(self):
        """Legacy 'file' mode should be treated as 'manual'."""
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="file", bgm_file=None)
        builder._ai_bgm_path = "/tmp/preset.wav"

        result = _resolve_bgm_path(builder)
        assert result == "/tmp/preset.wav"

    def test_legacy_ai_mode_maps_to_manual(self):
        """Legacy 'ai' mode should be treated as 'manual'."""
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="ai", bgm_file=None)
        builder._ai_bgm_path = "/tmp/preset.wav"

        result = _resolve_bgm_path(builder)
        assert result == "/tmp/preset.wav"
