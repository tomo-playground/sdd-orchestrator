"""Ken Burns scene-level preset resolution tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.video.filters import resolve_scene_preset


def _make_builder(global_preset: str = "random", scenes: list | None = None) -> MagicMock:
    """Create a minimal mock VideoBuilder for resolve_scene_preset."""
    builder = MagicMock()
    builder.ken_burns_preset = global_preset
    builder.project_id = 1

    if scenes is None:
        scenes = [MagicMock(ken_burns_preset=None)]
    builder.request.scenes = scenes
    return builder


class TestResolveScenePreset:
    """Tests for per-scene Ken Burns preset resolution."""

    def test_per_scene_preset_takes_priority(self):
        """씬별 ken_burns_preset이 전역보다 우선."""
        scene = MagicMock(ken_burns_preset="zoom_in_center")
        builder = _make_builder(global_preset="pan_left", scenes=[scene])
        result = resolve_scene_preset(builder, 0)
        assert result == "zoom_in_center"

    def test_per_scene_none_falls_to_global(self):
        """씬별 preset이 None이면 전역 fallback."""
        scene = MagicMock(ken_burns_preset=None)
        builder = _make_builder(global_preset="pan_right", scenes=[scene])
        result = resolve_scene_preset(builder, 0)
        assert result == "pan_right"

    def test_per_scene_none_string_falls_to_global(self):
        """씬별 preset이 'none'이면 전역 fallback (효과 없음 의도가 아닌 한)."""
        scene = MagicMock(ken_burns_preset="none")
        builder = _make_builder(global_preset="zoom_in_top", scenes=[scene])
        # 'none' falls through to global because it's "no effect"
        result = resolve_scene_preset(builder, 0)
        assert result == "zoom_in_top"

    def test_global_random_used_when_no_per_scene(self):
        """전역이 'random'이고 씬별 없으면 random에서 선택."""
        scene = MagicMock(ken_burns_preset=None)
        builder = _make_builder(global_preset="random", scenes=[scene])
        result = resolve_scene_preset(builder, 0)
        # Should return something from RANDOM_ELIGIBLE
        from services.motion import RANDOM_ELIGIBLE

        assert result in RANDOM_ELIGIBLE

    def test_global_fixed_preset_used_when_no_per_scene(self):
        """전역이 고정 프리셋이고 씬별 없으면 전역 사용."""
        scene = MagicMock(ken_burns_preset=None)
        builder = _make_builder(global_preset="slow_zoom", scenes=[scene])
        result = resolve_scene_preset(builder, 0)
        assert result == "slow_zoom"

    def test_per_scene_overrides_global_random(self):
        """전역이 random이어도 씬별 preset이 있으면 씬별 우선."""
        scene = MagicMock(ken_burns_preset="pan_down_vertical")
        builder = _make_builder(global_preset="random", scenes=[scene])
        result = resolve_scene_preset(builder, 0)
        assert result == "pan_down_vertical"

    def test_multiple_scenes_mixed(self):
        """여러 씬에서 혼합 사용: 일부 씬별, 일부 전역."""
        scenes = [
            MagicMock(ken_burns_preset="zoom_out_center"),
            MagicMock(ken_burns_preset=None),
            MagicMock(ken_burns_preset="pan_left"),
        ]
        builder = _make_builder(global_preset="slow_zoom", scenes=scenes)

        assert resolve_scene_preset(builder, 0) == "zoom_out_center"
        assert resolve_scene_preset(builder, 1) == "slow_zoom"
        assert resolve_scene_preset(builder, 2) == "pan_left"
