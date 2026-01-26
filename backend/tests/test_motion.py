"""Unit tests for Ken Burns motion effects module."""

import pytest

from services.motion import (
    PRESETS,
    RANDOM_ELIGIBLE,
    KenBurnsParams,
    build_zoompan_filter,
    get_preset,
    get_random_preset,
    resolve_preset_name,
)


class TestKenBurnsParams:
    """Tests for KenBurnsParams dataclass."""

    def test_default_values(self):
        """Default params should have no effect (zoom=1, center position)."""
        params = KenBurnsParams()
        assert params.zoom_start == 1.0
        assert params.zoom_end == 1.0
        assert params.x_start == 0.5
        assert params.x_end == 0.5
        assert params.y_start == 0.5
        assert params.y_end == 0.5

    def test_custom_values(self):
        """Custom params should be stored correctly."""
        params = KenBurnsParams(
            zoom_start=1.0, zoom_end=1.15,
            x_start=0.3, x_end=0.7,
            y_start=0.4, y_end=0.6
        )
        assert params.zoom_start == 1.0
        assert params.zoom_end == 1.15
        assert params.x_start == 0.3
        assert params.x_end == 0.7


class TestPresets:
    """Tests for preset definitions."""

    def test_all_presets_exist(self):
        """All expected presets should be defined."""
        expected = [
            "none", "slow_zoom", "zoom_in_center", "zoom_out_center",
            "pan_left", "pan_right", "pan_up", "pan_down",
            "zoom_pan_left", "zoom_pan_right"
        ]
        for name in expected:
            assert name in PRESETS, f"Missing preset: {name}"

    def test_none_preset_has_no_effect(self):
        """'none' preset should have no zoom or pan."""
        params = PRESETS["none"]
        assert params.zoom_start == params.zoom_end == 1.0
        assert params.x_start == params.x_end == 0.5
        assert params.y_start == params.y_end == 0.5

    def test_zoom_in_center_zooms_in(self):
        """zoom_in_center should increase zoom."""
        params = PRESETS["zoom_in_center"]
        assert params.zoom_end > params.zoom_start
        assert params.x_start == params.x_end  # No pan

    def test_zoom_out_center_zooms_out(self):
        """zoom_out_center should decrease zoom."""
        params = PRESETS["zoom_out_center"]
        assert params.zoom_end < params.zoom_start

    def test_pan_left_moves_right(self):
        """pan_left should move view from left to right (x increases)."""
        params = PRESETS["pan_left"]
        assert params.x_end > params.x_start
        assert params.zoom_start == params.zoom_end  # No zoom

    def test_pan_right_moves_left(self):
        """pan_right should move view from right to left (x decreases)."""
        params = PRESETS["pan_right"]
        assert params.x_end < params.x_start

    def test_combo_preset_has_both(self):
        """zoom_pan_left should have both zoom and pan."""
        params = PRESETS["zoom_pan_left"]
        assert params.zoom_end > params.zoom_start  # Zoom in
        assert params.x_end > params.x_start  # Pan left to right

    def test_random_eligible_excludes_special(self):
        """Random eligible list should not include none, slow_zoom, or random."""
        assert "none" not in RANDOM_ELIGIBLE
        assert "slow_zoom" not in RANDOM_ELIGIBLE
        assert "random" not in RANDOM_ELIGIBLE
        assert len(RANDOM_ELIGIBLE) == 14  # 8 original + 6 vertical presets


class TestGetPreset:
    """Tests for get_preset function."""

    def test_valid_preset(self):
        """Should return correct preset for valid name."""
        params = get_preset("zoom_in_center")
        assert params == PRESETS["zoom_in_center"]

    def test_invalid_preset_returns_none(self):
        """Should return 'none' preset for invalid name."""
        params = get_preset("invalid_preset_name")
        assert params == PRESETS["none"]

    def test_empty_string_returns_none(self):
        """Should return 'none' preset for empty string."""
        params = get_preset("")
        assert params == PRESETS["none"]


class TestGetRandomPreset:
    """Tests for get_random_preset function."""

    def test_returns_eligible_preset(self):
        """Should return a preset from RANDOM_ELIGIBLE."""
        name, params = get_random_preset()
        assert name in RANDOM_ELIGIBLE
        assert params == PRESETS[name]

    def test_seed_reproducibility(self):
        """Same seed should return same preset."""
        name1, _ = get_random_preset(seed=12345)
        name2, _ = get_random_preset(seed=12345)
        assert name1 == name2

    def test_different_seeds_may_differ(self):
        """Different seeds should (likely) return different presets."""
        results = set()
        for seed in range(100):
            name, _ = get_random_preset(seed=seed)
            results.add(name)
        # Should have multiple different presets across 100 seeds
        assert len(results) > 1


class TestBuildZoompanFilter:
    """Tests for build_zoompan_filter function."""

    def test_basic_filter_format(self):
        """Should return properly formatted zoompan filter."""
        params = KenBurnsParams()
        result = build_zoompan_filter(params, 1080, 1920, 75)

        assert result.startswith("zoompan=")
        assert "z=" in result
        assert "x=" in result
        assert "y=" in result
        assert "d=75" in result
        assert "s=1080x1920" in result
        assert "fps=25" in result

    def test_zoom_in_filter(self):
        """Zoom in preset should have increasing z expression."""
        params = PRESETS["zoom_in_center"]
        result = build_zoompan_filter(params, 1080, 1920, 75)

        # Should contain positive zoom delta
        assert "z='(1.0+" in result
        assert "*on/75)" in result

    def test_pan_filter(self):
        """Pan preset should have changing x expression."""
        params = PRESETS["pan_left"]
        result = build_zoompan_filter(params, 1080, 1920, 75)

        # x should interpolate from 0.3 to 0.7
        assert "*(0.3+" in result

    def test_intensity_increases_effect(self):
        """Higher intensity should increase effect magnitude."""
        params = PRESETS["zoom_in_center"]

        result_1x = build_zoompan_filter(params, 1080, 1920, 75, intensity=1.0)
        result_2x = build_zoompan_filter(params, 1080, 1920, 75, intensity=2.0)

        # Extract zoom delta from filter (rough check)
        # 1.0x intensity: zoom 1.0 -> 1.15 (delta 0.15)
        # 2.0x intensity: zoom 1.0 -> 1.30 (delta 0.30)
        assert "0.15" in result_1x or "0.1499" in result_1x
        assert "0.3" in result_2x or "0.29" in result_2x

    def test_intensity_clamped(self):
        """Intensity should be clamped to 0.5-2.0 range."""
        params = PRESETS["zoom_in_center"]

        # Very low intensity should be clamped to 0.5
        result_low = build_zoompan_filter(params, 1080, 1920, 75, intensity=0.1)
        # Very high intensity should be clamped to 2.0
        result_high = build_zoompan_filter(params, 1080, 1920, 75, intensity=5.0)

        # Both should produce valid filters (not error)
        assert "zoompan=" in result_low
        assert "zoompan=" in result_high

    def test_custom_fps(self):
        """Should use custom fps value."""
        params = KenBurnsParams()
        result = build_zoompan_filter(params, 1080, 1920, 75, fps=30)
        assert "fps=30" in result


class TestResolvePresetName:
    """Tests for resolve_preset_name function."""

    def test_valid_preset(self):
        """Valid preset name should be returned."""
        result = resolve_preset_name("zoom_in_center")
        assert result == "zoom_in_center"

    def test_none_returns_none(self):
        """'none' should return 'none'."""
        result = resolve_preset_name("none")
        assert result == "none"

    def test_null_returns_none(self):
        """None should return 'none'."""
        result = resolve_preset_name(None)
        assert result == "none"

    def test_empty_string_returns_none(self):
        """Empty string should return 'none'."""
        result = resolve_preset_name("")
        assert result == "none"

    def test_random_preset(self):
        """'random' should be passed through."""
        result = resolve_preset_name("random")
        assert result == "random"
