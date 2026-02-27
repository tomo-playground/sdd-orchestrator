"""Tests for Phase 18-P4: Stage → Rendering integration.

P4-1: Transition auto-select (4 tests)
P4-2: Ken Burns alternation for same-background scenes (3 tests)
P4-4: Reference AdaIN indoor/outdoor weight adjustment (4 tests)
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# ── P4-1: Transition auto-select ─────────────────────────────────


def _make_builder(transition_type: str, scenes: list[dict], project_id: str = "test_proj") -> MagicMock:
    """Create a mock VideoBuilder with scenes."""
    builder = MagicMock()
    builder.transition_type = transition_type
    builder.project_id = project_id
    builder.request = SimpleNamespace(
        scenes=[SimpleNamespace(**s) for s in scenes],
    )
    return builder


class TestAutoTransition:
    def test_same_background_returns_fade(self):
        from services.video.effects import resolve_scene_transition

        builder = _make_builder(
            "auto",
            [
                {"background_id": 1},
                {"background_id": 1},
            ],
        )
        assert resolve_scene_transition(builder, 1) == "fade"

    def test_different_background_returns_slide(self):
        from constants.transition import LOCATION_CHANGE_TRANSITIONS
        from services.video.effects import resolve_scene_transition

        builder = _make_builder(
            "auto",
            [
                {"background_id": 1},
                {"background_id": 2},
            ],
        )
        result = resolve_scene_transition(builder, 1)
        assert result in LOCATION_CHANGE_TRANSITIONS

    def test_null_backgrounds_returns_fade(self):
        from services.video.effects import resolve_scene_transition

        builder = _make_builder(
            "auto",
            [
                {"background_id": None},
                {"background_id": None},
            ],
        )
        assert resolve_scene_transition(builder, 1) == "fade"

    def test_non_auto_mode_preserves_existing_behavior(self):
        from services.video.effects import resolve_scene_transition

        # Fixed mode
        builder = _make_builder(
            "fade",
            [
                {"background_id": 1},
                {"background_id": 2},
            ],
        )
        assert resolve_scene_transition(builder, 1) == "fade"

        # Random mode
        from constants.transition import RANDOM_ELIGIBLE

        builder = _make_builder(
            "random",
            [
                {"background_id": 1},
                {"background_id": 2},
            ],
        )
        result = resolve_scene_transition(builder, 1)
        assert result in RANDOM_ELIGIBLE


# ── P4-2: Ken Burns alternation ──────────────────────────────────


class TestKenBurnsAlternation:
    def test_same_bg_adjacent_scenes_get_different_presets(self):
        from services.video.filters import resolve_scene_preset

        builder = _make_builder(
            "random",
            [
                {"background_id": 5, "ken_burns_preset": None},
                {"background_id": 5, "ken_burns_preset": None},
            ],
        )
        builder.ken_burns_preset = "random"

        # Resolve scene 0 first to populate _resolved_presets
        preset_0 = resolve_scene_preset(builder, 0)
        builder._resolved_presets = {0: preset_0}

        # Scene 1 should get a different preset
        preset_1 = resolve_scene_preset(builder, 1)
        assert preset_0 != preset_1

    def test_different_bg_no_alternation(self):
        """Different backgrounds → no alternation logic, uses normal random."""
        from services.motion import RANDOM_ELIGIBLE
        from services.video.filters import resolve_scene_preset

        builder = _make_builder(
            "random",
            [
                {"background_id": 5, "ken_burns_preset": None},
                {"background_id": 6, "ken_burns_preset": None},
            ],
        )
        builder.ken_burns_preset = "random"
        builder._resolved_presets = {0: "zoom_in_center"}

        preset_1 = resolve_scene_preset(builder, 1)
        assert preset_1 in RANDOM_ELIGIBLE

    def test_per_scene_override_takes_priority(self):
        from services.video.filters import resolve_scene_preset

        builder = _make_builder(
            "random",
            [
                {"background_id": 5, "ken_burns_preset": None},
                {"background_id": 5, "ken_burns_preset": "pan_left"},
            ],
        )
        builder.ken_burns_preset = "random"
        builder._resolved_presets = {0: "zoom_in_center"}

        assert resolve_scene_preset(builder, 1) == "pan_left"


# ── P4-4: Reference AdaIN weight ─────────────────────────────────


class TestClassifyIndoorOutdoor:
    def test_classify_indoor_tags(self):
        from services.generation_controlnet import classify_indoor_outdoor

        assert classify_indoor_outdoor(["cafe", "indoors"]) == "indoor"

    def test_classify_outdoor_tags(self):
        from services.generation_controlnet import classify_indoor_outdoor

        assert classify_indoor_outdoor(["park", "outdoors"]) == "outdoor"

    def test_mixed_returns_none(self):
        from services.generation_controlnet import classify_indoor_outdoor

        assert classify_indoor_outdoor(["cafe", "park"]) is None

    def test_adain_weight_varies_by_location_type(self):
        """Verify that _apply_reference_adain_from_asset uses different weights."""
        from unittest.mock import mock_open, patch

        from services.generation_controlnet import _apply_reference_adain_from_asset

        env_asset = SimpleNamespace(local_path="/tmp/test.png")
        request = SimpleNamespace(environment_reference_id=1)
        fake_data = b"fake_image_data"

        for location_type, expected_weight in [
            ("indoor", 0.40),
            ("outdoor", 0.25),
            (None, 0.35),
        ]:
            args_list: list[dict] = []
            with patch("os.path.exists", return_value=True), patch("builtins.open", mock_open(read_data=fake_data)):
                _apply_reference_adain_from_asset(env_asset, request, args_list, location_type)
            assert len(args_list) == 1
            assert args_list[0]["weight"] == pytest.approx(expected_weight)
