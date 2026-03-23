"""Tests for BGM ducking filter chain, safety clamp, and fade-out."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.video.effects import _apply_ducked_bgm, _apply_simple_bgm, apply_bgm


def _make_builder(
    total_dur: float = 45.0,
    scene_durations: list[float] | None = None,
    bgm_vol: float = 0.3,
    ducking: bool = True,
    ducking_threshold: float = 0.02,
) -> MagicMock:
    builder = MagicMock()
    builder._total_dur = total_dur
    builder.scene_durations = scene_durations if scene_durations is not None else [15.0, 15.0, 15.0]
    builder.request = SimpleNamespace(
        bgm_volume=bgm_vol,
        audio_ducking=ducking,
        ducking_threshold=ducking_threshold,
        bgm_mode="manual",
    )
    builder._ai_bgm_path = "/tmp/bgm.wav"
    builder._map_a = "[a_mix]"
    builder._next_input_idx = 6
    builder.filters = []
    builder.input_args = []
    builder.project_id = "test_123"
    return builder


class TestApplyBgmSafetyClamp:
    """apply_bgm() _total_dur safety clamp tests."""

    @patch("services.video.effects._build_bgm_loop_filters", return_value="[bgm_looped]")
    @patch("services.video.effects._resolve_bgm_path", return_value="/tmp/bgm.wav")
    def test_zero_total_dur_uses_scene_durations(self, _mock_path, _mock_loop):
        builder = _make_builder(total_dur=0.0, scene_durations=[10.0, 20.0])
        apply_bgm(builder)
        assert builder._total_dur == 30.0  # sum of scene_durations

    @patch("services.video.effects._build_bgm_loop_filters", return_value="[bgm_looped]")
    @patch("services.video.effects._resolve_bgm_path", return_value="/tmp/bgm.wav")
    def test_negative_total_dur_uses_scene_durations(self, _mock_path, _mock_loop):
        builder = _make_builder(total_dur=-5.0, scene_durations=[8.0, 12.0])
        apply_bgm(builder)
        assert builder._total_dur == 20.0

    @patch("services.video.effects._resolve_bgm_path", return_value="/tmp/bgm.wav")
    def test_zero_total_dur_empty_scenes_skips_bgm(self, _mock_path):
        builder = _make_builder(total_dur=0.0, scene_durations=[])
        initial_input_len = len(builder.input_args)
        apply_bgm(builder)
        # No BGM input added (early return)
        assert len(builder.input_args) == initial_input_len

    @patch("services.video.effects._build_bgm_loop_filters", return_value="[bgm_looped]")
    @patch("services.video.effects._resolve_bgm_path", return_value="/tmp/bgm.wav")
    def test_positive_total_dur_unchanged(self, _mock_path, _mock_loop):
        builder = _make_builder(total_dur=45.0)
        apply_bgm(builder)
        assert builder._total_dur == 45.0  # Not modified


class TestDuckedBgmFilterChain:
    """_apply_ducked_bgm filter chain correctness tests."""

    def test_ducked_filter_count(self):
        builder = _make_builder()
        _apply_ducked_bgm(builder, "[bgm_looped]", 0.3)
        # Should produce 4 filters: asplit, atrim+vol+fade, sidechaincompress, amix
        assert len(builder.filters) == 4

    def test_ducked_has_asplit(self):
        builder = _make_builder()
        _apply_ducked_bgm(builder, "[bgm_looped]", 0.3)
        assert "asplit=2" in builder.filters[0]

    def test_ducked_has_sidechaincompress(self):
        builder = _make_builder()
        _apply_ducked_bgm(builder, "[bgm_looped]", 0.3)
        assert any("sidechaincompress" in f for f in builder.filters)

    def test_ducked_threshold_reflected(self):
        builder = _make_builder(ducking_threshold=0.05)
        _apply_ducked_bgm(builder, "[bgm_looped]", 0.3)
        sc_filter = [f for f in builder.filters if "sidechaincompress" in f][0]
        assert "threshold=0.05" in sc_filter

    def test_ducked_has_amix(self):
        builder = _make_builder()
        _apply_ducked_bgm(builder, "[bgm_looped]", 0.3)
        assert any("amix=inputs=2" in f for f in builder.filters)

    def test_ducked_has_fade_out(self):
        builder = _make_builder(total_dur=45.0)
        _apply_ducked_bgm(builder, "[bgm_looped]", 0.3)
        atrim_filter = builder.filters[1]
        assert "afade=t=out:st=43" in atrim_filter  # 45 - 2 = 43

    def test_ducked_atrim_matches_total_dur(self):
        builder = _make_builder(total_dur=30.0)
        _apply_ducked_bgm(builder, "[bgm_looped]", 0.3)
        atrim_filter = builder.filters[1]
        assert "atrim=duration=30.0" in atrim_filter


class TestSimpleBgmFilterChain:
    """_apply_simple_bgm filter chain correctness tests."""

    def test_simple_filter_count(self):
        builder = _make_builder()
        _apply_simple_bgm(builder, "[bgm_looped]", 0.3)
        # Should produce 2 filters: atrim+vol+fade, amix
        assert len(builder.filters) == 2

    def test_simple_has_fade_out(self):
        builder = _make_builder(total_dur=60.0)
        _apply_simple_bgm(builder, "[bgm_looped]", 0.3)
        assert "afade=t=out:st=58" in builder.filters[0]  # 60 - 2 = 58

    def test_simple_no_sidechaincompress(self):
        builder = _make_builder()
        _apply_simple_bgm(builder, "[bgm_looped]", 0.3)
        assert not any("sidechaincompress" in f for f in builder.filters)

    def test_simple_has_amix(self):
        builder = _make_builder()
        _apply_simple_bgm(builder, "[bgm_looped]", 0.3)
        assert any("amix=inputs=2" in f for f in builder.filters)
