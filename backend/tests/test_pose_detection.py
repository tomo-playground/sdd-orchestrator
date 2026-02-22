"""Tests for pose mapping, detection, and preprocessor settings."""

from __future__ import annotations

import pytest

from services.controlnet import (
    POSE_MAPPING,
    build_combined_controlnet_args,
    build_controlnet_args,
    detect_pose_from_prompt,
)


class TestPoseMapping:
    """Verify POSE_MAPPING integrity."""

    def test_pose_count(self):
        """28 poses: 18 original + 9 daily-life + 1 thumbs_up."""
        assert len(POSE_MAPPING) == 28

    def test_all_filenames_are_png(self):
        """Every mapped filename ends with .png."""
        for name, filename in POSE_MAPPING.items():
            assert filename.endswith(".png"), f"'{name}' maps to non-PNG: {filename}"

    def test_no_duplicate_filenames(self):
        """No two poses share the same filename."""
        filenames = list(POSE_MAPPING.values())
        assert len(filenames) == len(set(filenames)), "Duplicate filenames found"

    def test_original_18_poses_present(self):
        """All original 18 poses still exist."""
        original = [
            "standing",
            "waving",
            "arms up",
            "arms crossed",
            "hands on hips",
            "looking at viewer",
            "from behind",
            "sitting",
            "chin rest",
            "leaning",
            "walking",
            "running",
            "jumping",
            "lying",
            "kneeling",
            "crouching",
            "pointing forward",
            "covering face",
        ]
        for pose in original:
            assert pose in POSE_MAPPING, f"Original pose missing: {pose}"

    def test_new_9_poses_present(self):
        """All 9 daily-life poses exist."""
        new_poses = [
            "holding object",
            "eating",
            "cooking",
            "holding umbrella",
            "writing",
            "profile standing",
            "standing looking up",
            "leaning wall",
            "sitting eating",
        ]
        for pose in new_poses:
            assert pose in POSE_MAPPING, f"New pose missing: {pose}"

    def test_thumbs_up_pose_present(self):
        """thumbs_up pose exists."""
        assert "thumbs up" in POSE_MAPPING
        assert POSE_MAPPING["thumbs up"] == "standing_thumbs_up.png"


class TestPoseDetection:
    """Test detect_pose_from_prompt logic (exact match, longest-match priority)."""

    # --- Exact match tests ---
    @pytest.mark.parametrize(
        "pose_name",
        [
            "eating",
            "cooking",
            "writing",
            "holding umbrella",
            "holding object",
            "leaning wall",
            "standing looking up",
            "profile standing",
            "standing",
            "sitting",
            "waving",
            "from behind",
        ],
    )
    def test_exact_match_in_prompt(self, pose_name: str):
        """Pose name found in prompt string returns that pose."""
        prompt = f"1girl, {pose_name}, indoors"
        assert detect_pose_from_prompt(prompt) == pose_name

    # --- Longest-match priority tests ---
    def test_longest_match_profile_standing_over_standing(self):
        """'profile standing' (longer) wins over 'standing'."""
        prompt = "1girl, profile standing, indoors"
        assert detect_pose_from_prompt(prompt) == "profile standing"

    def test_longest_match_standing_looking_up_over_standing(self):
        """'standing looking up' (longer) wins over 'standing'."""
        prompt = "1girl, standing looking up, outdoors"
        assert detect_pose_from_prompt(prompt) == "standing looking up"

    def test_longest_match_sitting_eating_over_eating(self):
        """'sitting eating' (longer) wins over 'sitting' and 'eating'."""
        prompt = "1girl, sitting eating, table"
        assert detect_pose_from_prompt(prompt) == "sitting eating"

    def test_longest_match_holding_umbrella_over_holding_object(self):
        """'holding umbrella' (longer) wins over 'holding object' if both present."""
        prompt = "1girl, holding umbrella, rain"
        assert detect_pose_from_prompt(prompt) == "holding umbrella"

    # --- Case insensitive ---
    def test_case_insensitive(self):
        """Detection is case-insensitive."""
        prompt = "1girl, Standing, indoors"
        assert detect_pose_from_prompt(prompt) == "standing"

    def test_case_insensitive_mixed(self):
        """Mixed case still matches."""
        prompt = "1girl, From Behind, dark"
        assert detect_pose_from_prompt(prompt) == "from behind"

    # --- Edge cases ---
    def test_empty_prompt_returns_none(self):
        assert detect_pose_from_prompt("") is None

    def test_no_pose_in_prompt_returns_none(self):
        prompt = "blue_sky, sunshine, flowers"
        assert detect_pose_from_prompt(prompt) is None

    def test_partial_mismatch_no_false_positive(self):
        """Substring that is not a complete pose key doesn't match spuriously."""
        # 'lean' is not a pose key, only 'leaning' is
        prompt = "1girl, lean, outdoors"
        assert detect_pose_from_prompt(prompt) is None


class TestControlnetArgs:
    """Verify ControlNet args builder for openpose."""

    def test_build_controlnet_args_default_preprocessor(self):
        """Default openpose uses openpose module for runtime skeleton extraction."""
        args = build_controlnet_args(
            input_image="fake_b64",
            model="openpose",
            weight=1.0,
        )
        assert args["module"] == "openpose"
        assert args["model"] == "control_v11p_sd15_openpose [cab727d4]"

    def test_build_controlnet_args_explicit_preprocessor(self):
        """Explicit preprocessor overrides default module."""
        args = build_controlnet_args(
            input_image="fake_b64",
            model="openpose",
            weight=0.8,
            preprocessor="none",
        )
        assert args["module"] == "none"

    def test_combined_args_uses_default_preprocessor(self):
        """build_combined_controlnet_args uses default openpose preprocessor."""
        args = build_combined_controlnet_args(
            pose_image="fake_b64",
            pose_weight=0.8,
        )
        assert len(args) == 1
        assert args[0]["module"] == "openpose"
