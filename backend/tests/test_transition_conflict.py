"""Tests for transition / Ken Burns direction conflict prevention."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.video.effects import (
    DIRECTION_CONFLICT_MAP,
    _check_direction_conflict,
    resolve_scene_transition,
)


def _make_builder(
    transition_type: str = "auto",
    scenes: list | None = None,
) -> MagicMock:
    builder = MagicMock()
    builder.transition_type = transition_type
    builder.project_id = "test_123"
    if scenes is None:
        scenes = [MagicMock(ken_burns_preset=None, background_id=None)]
    builder.request.scenes = scenes
    return builder


class TestCheckDirectionConflict:
    """_check_direction_conflict() unit tests."""

    def test_slideleft_pan_left_conflicts(self):
        """slideleft + pan_left -> fade."""
        scene = MagicMock(ken_burns_preset="pan_left")
        builder = _make_builder(scenes=[scene, scene])
        result = _check_direction_conflict(builder, 1, "slideleft")
        assert result == "fade"

    def test_slideright_pan_right_conflicts(self):
        """slideright + pan_right -> fade."""
        scene = MagicMock(ken_burns_preset="pan_right")
        builder = _make_builder(scenes=[scene, scene])
        result = _check_direction_conflict(builder, 1, "slideright")
        assert result == "fade"

    def test_wipeleft_zoom_pan_left_conflicts(self):
        """wipeleft + zoom_pan_left -> fade."""
        scene = MagicMock(ken_burns_preset="zoom_pan_left")
        builder = _make_builder(scenes=[scene, scene])
        result = _check_direction_conflict(builder, 1, "wipeleft")
        assert result == "fade"

    def test_slideup_pan_up_vertical_conflicts(self):
        """slideup + pan_up_vertical -> fade."""
        scene = MagicMock(ken_burns_preset="pan_up_vertical")
        builder = _make_builder(scenes=[scene, scene])
        result = _check_direction_conflict(builder, 1, "slideup")
        assert result == "fade"

    def test_slidedown_pan_zoom_down_conflicts(self):
        """slidedown + pan_zoom_down -> fade."""
        scene = MagicMock(ken_burns_preset="pan_zoom_down")
        builder = _make_builder(scenes=[scene, scene])
        result = _check_direction_conflict(builder, 1, "slidedown")
        assert result == "fade"

    def test_no_conflict_different_directions(self):
        """slideleft + pan_up -> no conflict, keep slideleft."""
        scene = MagicMock(ken_burns_preset="pan_up")
        builder = _make_builder(scenes=[scene, scene])
        result = _check_direction_conflict(builder, 1, "slideleft")
        assert result == "slideleft"

    def test_no_conflict_zoom_only(self):
        """slideleft + zoom_in_center -> no conflict."""
        scene = MagicMock(ken_burns_preset="zoom_in_center")
        builder = _make_builder(scenes=[scene, scene])
        result = _check_direction_conflict(builder, 1, "slideleft")
        assert result == "slideleft"

    def test_fade_always_safe(self):
        """fade has no direction, always safe."""
        scene = MagicMock(ken_burns_preset="pan_left")
        builder = _make_builder(scenes=[scene, scene])
        result = _check_direction_conflict(builder, 1, "fade")
        assert result == "fade"

    def test_no_kb_preset_skips_check(self):
        """No ken_burns_preset -> skip conflict check."""
        scene = MagicMock(ken_burns_preset=None)
        builder = _make_builder(scenes=[scene, scene])
        result = _check_direction_conflict(builder, 1, "slideleft")
        assert result == "slideleft"

    def test_circleopen_always_safe(self):
        """circleopen has no direction mapping, always safe."""
        scene = MagicMock(ken_burns_preset="pan_left")
        builder = _make_builder(scenes=[scene, scene])
        result = _check_direction_conflict(builder, 1, "circleopen")
        assert result == "circleopen"


class TestResolveSceneTransitionWithConflict:
    """Integration: resolve_scene_transition + direction conflict."""

    def test_auto_location_change_conflict(self):
        """Auto mode location change -> slideleft chosen but conflicts with pan_left -> fade."""
        prev = MagicMock(ken_burns_preset=None, background_id="bg_a")
        curr = MagicMock(ken_burns_preset="pan_left", background_id="bg_b")
        builder = _make_builder(transition_type="auto", scenes=[prev, curr])

        result = resolve_scene_transition(builder, 1)
        # The auto-chosen transition might be slideleft/wipeleft which conflicts,
        # or slideright/wiperight which doesn't. Assert it's never a conflicting one.
        conflicting = DIRECTION_CONFLICT_MAP.get(result, set())
        assert "pan_left" not in conflicting

    def test_explicit_type_no_conflict_kept(self):
        """Explicit transition_type="dissolve" has no direction, kept as-is."""
        scene = MagicMock(ken_burns_preset="pan_left")
        builder = _make_builder(transition_type="dissolve", scenes=[scene, scene])
        result = resolve_scene_transition(builder, 1)
        assert result == "dissolve"

    def test_auto_same_background_is_fade(self):
        """Same background -> fade (no conflict possible)."""
        scene = MagicMock(ken_burns_preset="pan_left", background_id="bg_a")
        builder = _make_builder(transition_type="auto", scenes=[scene, scene])
        result = resolve_scene_transition(builder, 1)
        assert result == "fade"
