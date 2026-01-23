"""
Tests for deterministic/fixed seed behavior.

These tests verify that the same inputs produce the same outputs
when using fixed seeds, which is essential for VRT reliability.
"""

import random
from pathlib import Path

import pytest
from PIL import Image

from constants.testing import (
    VRTConfig,
    get_test_seed,
    create_seeded_random,
    get_test_views_time,
    get_test_avatar_color,
)
from logic import render_subtitle_image, _build_post_meta
from tests.vrt.compare import VRTComparison, pil_to_numpy


class TestDeterministicSeeds:
    """Tests for seed consistency."""

    def test_fixed_seed_consistency(self):
        """Verify that the same seed produces the same sequence."""
        rng1 = create_seeded_random(42)
        rng2 = create_seeded_random(42)

        # Generate sequences
        seq1 = [rng1.randint(0, 1000) for _ in range(10)]
        seq2 = [rng2.randint(0, 1000) for _ in range(10)]

        assert seq1 == seq2, "Same seed should produce same sequence"

    def test_get_test_seed_deterministic(self):
        """Verify that get_test_seed returns consistent values."""
        seed1 = get_test_seed("test_case_1")
        seed2 = get_test_seed("test_case_1")
        seed3 = get_test_seed("test_case_2")

        assert seed1 == seed2, "Same name should produce same seed"
        assert seed1 != seed3, "Different names should produce different seeds"

    def test_views_time_deterministic(self):
        """Verify that views/time generation is deterministic with seed."""
        views1, time1 = get_test_views_time(seed=100)
        views2, time2 = get_test_views_time(seed=100)
        views3, time3 = get_test_views_time(seed=200)

        assert views1 == views2, "Same seed should produce same views"
        assert time1 == time2, "Same seed should produce same time"
        # Different seed may or may not produce different values (depends on pool)

    def test_avatar_color_deterministic(self):
        """Verify that avatar color generation is deterministic with seed."""
        color1 = get_test_avatar_color(seed=100)
        color2 = get_test_avatar_color(seed=100)

        assert color1 == color2, "Same seed should produce same color"
        assert len(color1) == 3, "Color should be RGB tuple"


class TestDeterministicRendering:
    """Tests for deterministic rendering output."""

    def test_subtitle_rendering_deterministic(
        self, vrt: VRTComparison, sample_font_path: Path
    ):
        """Verify that subtitle rendering is deterministic."""
        # Render twice with same parameters
        result1 = render_subtitle_image(
            lines=["결정론적 테스트"],
            width=1080,
            height=1920,
            font_path=str(sample_font_path),
            use_post_layout=False,
            post_layout_metrics=None,
        )

        result2 = render_subtitle_image(
            lines=["결정론적 테스트"],
            width=1080,
            height=1920,
            font_path=str(sample_font_path),
            use_post_layout=False,
            post_layout_metrics=None,
        )

        # Convert to numpy for comparison
        arr1 = pil_to_numpy(result1)
        arr2 = pil_to_numpy(result2)

        # Should be exactly identical
        assert (arr1 == arr2).all(), "Same inputs should produce identical output"

    def test_post_meta_deterministic(self):
        """Verify that post meta generation is deterministic."""
        # _build_post_meta uses _seeded_int which is deterministic
        meta1 = _build_post_meta(
            channel_name="test_ch",
            caption="테스트 캡션",
            title_text="제목",
        )

        meta2 = _build_post_meta(
            channel_name="test_ch",
            caption="테스트 캡션",
            title_text="제목",
        )

        assert meta1["display_name"] == meta2["display_name"]
        assert meta1["avatar_color"] == meta2["avatar_color"]


class TestTestModeConfiguration:
    """Tests for test mode configuration."""

    def test_test_mode_is_set(self):
        """Verify that test mode is automatically set in tests."""
        import os
        assert os.environ.get("VRT_TEST_MODE") == "1"

    def test_is_test_mode_returns_true(self):
        """Verify that is_test_mode() returns True during tests."""
        assert VRTConfig.is_test_mode() is True

    def test_get_sd_seed_returns_fixed(self):
        """Verify that SD seed is fixed in test mode."""
        seed = VRTConfig.get_sd_seed()
        assert seed == VRTConfig.SD_IMAGE_SEED
        assert seed != -1  # Not random

    def test_get_meta_random_is_seeded(self):
        """Verify that meta random is seeded in test mode."""
        rng1 = VRTConfig.get_meta_random()
        rng2 = VRTConfig.get_meta_random()

        # Both should produce the same sequence
        val1 = rng1.randint(0, 1000)
        val2 = rng2.randint(0, 1000)
        assert val1 == val2, "Meta random should be seeded in test mode"


class TestVRTWithFixedSeeds:
    """VRT tests that rely on fixed seeds."""

    def test_vrt_subtitle_fixed_seed(
        self, vrt: VRTComparison, sample_font_path: Path, fixed_seed: int
    ):
        """VRT test using fixed seed for subtitle."""
        # Use fixed seed in test name for unique golden master
        result = render_subtitle_image(
            lines=[f"Fixed Seed: {fixed_seed}"],
            width=1080,
            height=1920,
            font_path=str(sample_font_path),
            use_post_layout=False,
            post_layout_metrics=None,
        )

        comparison = vrt.compare("deterministic/subtitle_fixed_seed.png", result)
        assert comparison.passed, f"VRT failed: {comparison.message}"

    def test_multiple_runs_identical(
        self, vrt: VRTComparison, sample_font_path: Path
    ):
        """Verify multiple test runs produce identical results."""
        # This test should always pass because seeds are fixed
        results = []
        for i in range(3):
            result = render_subtitle_image(
                lines=["반복 테스트"],
                width=1080,
                height=1920,
                font_path=str(sample_font_path),
                use_post_layout=False,
                post_layout_metrics=None,
            )
            results.append(pil_to_numpy(result))

        # All results should be identical
        for i in range(1, len(results)):
            assert (results[0] == results[i]).all(), f"Run {i} differs from run 0"
