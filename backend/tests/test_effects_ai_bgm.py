"""Unit tests for apply_bgm manual/auto modes in effects module."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.video.effects import (
    _build_bgm_loop_filters,
    _probe_duration,
    _resolve_bgm_path,
)


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


class TestProbeDuration:
    """Tests for _probe_duration."""

    @patch("subprocess.run")
    def test_returns_duration(self, mock_run):
        mock_run.return_value = MagicMock(stdout="30.5\n", returncode=0)
        assert _probe_duration("/tmp/bgm.wav") == 30.5

    @patch("subprocess.run")
    def test_returns_zero_on_failure(self, mock_run):
        mock_run.side_effect = Exception("ffprobe not found")
        assert _probe_duration("/tmp/bgm.wav") == 0.0


class TestBuildBgmLoopFilters:
    """Tests for _build_bgm_loop_filters (asplit + acrossfade)."""

    @patch("services.video.effects._probe_duration")
    def test_no_loop_when_bgm_longer(self, mock_probe):
        """BGM longer than video → no loop filters, return raw input label."""
        mock_probe.return_value = 60.0
        builder = MagicMock()
        builder._total_dur = 45.0
        builder.filters = []

        label = _build_bgm_loop_filters(builder, 5, "/tmp/bgm.wav")
        assert label == "[5:a]"
        assert len(builder.filters) == 0

    @patch("services.video.effects._probe_duration")
    def test_no_loop_when_bgm_equal(self, mock_probe):
        mock_probe.return_value = 45.0
        builder = MagicMock()
        builder._total_dur = 45.0
        builder.filters = []

        label = _build_bgm_loop_filters(builder, 5, "/tmp/bgm.wav")
        assert label == "[5:a]"

    @patch("services.video.effects._probe_duration")
    def test_no_loop_when_bgm_within_margin(self, mock_probe):
        """BGM 0.5s shorter than video → within 1s margin, no loop."""
        mock_probe.return_value = 44.5
        builder = MagicMock()
        builder._total_dur = 45.0
        builder.filters = []

        label = _build_bgm_loop_filters(builder, 5, "/tmp/bgm.wav")
        assert label == "[5:a]"

    @patch("services.video.effects._probe_duration")
    def test_loop_with_crossfade(self, mock_probe):
        """30s BGM for 45s video → asplit=2 + 1 acrossfade."""
        mock_probe.return_value = 30.0
        builder = MagicMock()
        builder._total_dur = 45.0
        builder.filters = []

        label = _build_bgm_loop_filters(builder, 5, "/tmp/bgm.wav")
        assert label == "[bgm_looped]"
        # asplit + 1 acrossfade
        assert len(builder.filters) == 2
        assert "asplit=2" in builder.filters[0]
        assert "acrossfade" in builder.filters[1]
        assert "[bgm_looped]" in builder.filters[1]

    @patch("services.video.effects._probe_duration")
    def test_multiple_loops(self, mock_probe):
        """10s BGM for 45s video → multiple copies with chained crossfades."""
        mock_probe.return_value = 10.0
        builder = MagicMock()
        builder._total_dur = 45.0
        builder.filters = []

        label = _build_bgm_loop_filters(builder, 5, "/tmp/bgm.wav")
        assert label == "[bgm_looped]"
        # 1 asplit + N-1 acrossfades
        copies = int(builder.filters[0].split("asplit=")[1].split("[")[0])
        assert copies >= 4
        assert len(builder.filters) == 1 + (copies - 1)

    @patch("services.video.effects._probe_duration")
    def test_probe_failure_uses_fallback_loop(self, mock_probe):
        """ffprobe failure → fallback to 3 copies with crossfade."""
        mock_probe.return_value = 0.0
        builder = MagicMock()
        builder._total_dur = 45.0
        builder.filters = []

        label = _build_bgm_loop_filters(builder, 5, "/tmp/bgm.wav")
        assert label == "[bgm_looped]"
        # 3 fallback copies: asplit=3 + 2 acrossfades
        assert len(builder.filters) == 3
        assert "asplit=3" in builder.filters[0]
        assert "acrossfade" in builder.filters[1]
        assert "[bgm_looped]" in builder.filters[2]
