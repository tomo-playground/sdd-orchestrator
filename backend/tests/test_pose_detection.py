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
            "standing", "waving", "arms up", "arms crossed",
            "hands on hips", "looking at viewer", "from behind",
            "sitting", "chin rest", "leaning",
            "walking", "running", "jumping", "lying",
            "kneeling", "crouching", "pointing forward", "covering face",
        ]
        for pose in original:
            assert pose in POSE_MAPPING, f"Original pose missing: {pose}"

    def test_new_9_poses_present(self):
        """All 9 daily-life poses exist."""
        new_poses = [
            "holding object", "eating", "cooking",
            "holding umbrella", "writing", "profile standing",
            "standing looking up", "leaning wall", "sitting eating",
        ]
        for pose in new_poses:
            assert pose in POSE_MAPPING, f"New pose missing: {pose}"

    def test_thumbs_up_pose_present(self):
        """thumbs_up pose exists."""
        assert "thumbs up" in POSE_MAPPING
        assert POSE_MAPPING["thumbs up"] == "standing_thumbs_up.png"


class TestPoseDetection:
    """Test detect_pose_from_prompt logic."""

    # --- Exact match tests ---
    @pytest.mark.parametrize("pose_name", [
        "eating", "cooking", "writing",
        "holding umbrella", "holding object",
        "leaning wall",
        "standing looking up", "profile standing",
    ])
    def test_exact_match_new_poses(self, pose_name: str):
        """New poses detected via exact tag match."""
        tags = [pose_name.replace(" ", "_")]
        result = detect_pose_from_prompt(tags)
        assert result == pose_name

    def test_sitting_eating_via_dining_synonym(self):
        """sitting_eating contains 'eating' substring so 'eating' wins on priority.
        Use unique synonyms (dining, meal) to match sitting eating."""
        # "sitting_eating" tag triggers "eating" first (higher priority, substring match)
        tags = ["sitting_eating"]
        assert detect_pose_from_prompt(tags) == "eating"

        # Use unique synonym to target sitting eating specifically
        tags = ["dining"]
        assert detect_pose_from_prompt(tags) == "sitting eating"

    def test_exact_match_standing(self):
        tags = ["standing", "1girl"]
        assert detect_pose_from_prompt(tags) == "standing"

    def test_exact_match_sitting(self):
        tags = ["sitting", "chair"]
        assert detect_pose_from_prompt(tags) == "sitting"

    # --- Synonym match tests ---
    def test_synonym_chopsticks_to_eating(self):
        tags = ["chopsticks", "table"]
        assert detect_pose_from_prompt(tags) == "eating"

    def test_synonym_chef_to_cooking(self):
        tags = ["chef", "apron"]
        assert detect_pose_from_prompt(tags) == "cooking"

    def test_synonym_umbrella_to_holding_umbrella(self):
        tags = ["umbrella", "rain"]
        assert detect_pose_from_prompt(tags) == "holding umbrella"

    def test_synonym_drawing_to_writing(self):
        tags = ["drawing", "desk"]
        assert detect_pose_from_prompt(tags) == "writing"

    def test_synonym_profile_to_profile_standing(self):
        tags = ["profile", "1girl"]
        assert detect_pose_from_prompt(tags) == "profile standing"

    def test_synonym_looking_up_to_standing_looking_up(self):
        tags = ["looking_up", "sky"]
        assert detect_pose_from_prompt(tags) == "standing looking up"

    def test_synonym_leaning_against_wall(self):
        tags = ["leaning_against_wall", "casual"]
        assert detect_pose_from_prompt(tags) == "leaning wall"

    def test_synonym_dining_to_sitting_eating(self):
        tags = ["dining", "restaurant"]
        assert detect_pose_from_prompt(tags) == "sitting eating"

    def test_synonym_holding_to_holding_object(self):
        tags = ["holding", "bag"]
        assert detect_pose_from_prompt(tags) == "holding object"

    def test_thumbs_up_exact(self):
        tags = ["thumbs_up", "1girl"]
        assert detect_pose_from_prompt(tags) == "thumbs up"

    def test_thumbs_up_synonym_approval(self):
        tags = ["approval", "smiling"]
        assert detect_pose_from_prompt(tags) == "thumbs up"

    # --- Priority tests ---
    def test_eating_before_sitting(self):
        """Eating is more specific than sitting and should win."""
        tags = ["eating", "sitting"]
        assert detect_pose_from_prompt(tags) == "eating"

    def test_cooking_before_standing(self):
        """Cooking is more specific than standing and should win."""
        tags = ["cooking", "standing"]
        assert detect_pose_from_prompt(tags) == "cooking"

    def test_waving_before_standing(self):
        tags = ["waving", "standing"]
        assert detect_pose_from_prompt(tags) == "waving"

    # --- Edge cases ---
    def test_empty_tags_returns_none(self):
        assert detect_pose_from_prompt([]) is None

    def test_unrelated_tags_returns_none(self):
        tags = ["blue_sky", "sunshine", "flowers"]
        assert detect_pose_from_prompt(tags) is None


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
