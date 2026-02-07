"""Unit tests for apply_bgm AI mode in effects module."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.video.effects import _resolve_bgm_path


class TestResolveBgmPath:
    """Tests for _resolve_bgm_path with file and AI modes."""

    def test_ai_mode_returns_ai_bgm_path(self):
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="ai")
        builder._ai_bgm_path = "/tmp/ai_bgm.wav"

        result = _resolve_bgm_path(builder)
        assert result == "/tmp/ai_bgm.wav"

    def test_ai_mode_returns_none_when_no_path(self):
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="ai")
        builder._ai_bgm_path = None

        result = _resolve_bgm_path(builder)
        assert result is None

    def test_ai_mode_does_not_fallthrough_to_file(self):
        """AI mode with no path should NOT try file-based BGM."""
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="ai", bgm_file="song.mp3")
        builder._ai_bgm_path = None

        with patch("services.video.effects.resolve_bgm_file") as mock_resolve:
            result = _resolve_bgm_path(builder)

        assert result is None
        mock_resolve.assert_not_called()

    @patch("services.video.effects.get_storage")
    @patch("services.video.effects.resolve_bgm_file")
    def test_file_mode_uses_resolve_bgm_file(self, mock_resolve, mock_storage):
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="file", bgm_file="song.mp3")
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
    def test_file_mode_none_when_no_bgm(self, mock_resolve, _mock_storage):
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="file", bgm_file=None)
        builder.project_id = "build_123"
        mock_resolve.return_value = None

        result = _resolve_bgm_path(builder)
        assert result is None
