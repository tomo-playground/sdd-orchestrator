"""Tests for ControlNet IP-Adapter weight clamping and finalize validation."""

from __future__ import annotations

from services.controlnet import (
    clamp_ip_adapter_weight,
)

# ── clamp_ip_adapter_weight ──────────────────────────────────────


class TestClampIpAdapterWeight:
    """clamp_ip_adapter_weight() direction-based clamping."""

    def test_front_pose_no_clamp(self):
        """Front-facing pose: weight passes through unchanged."""
        assert clamp_ip_adapter_weight(0.8, "standing") == 0.8

    def test_front_pose_high_weight(self):
        """Front-facing pose: even max weight is fine."""
        assert clamp_ip_adapter_weight(1.0, "standing") == 1.0

    def test_back_pose_clamp(self):
        """Back-facing pose: weight clamped to 0.2."""
        assert clamp_ip_adapter_weight(0.7, "from_behind") == 0.2

    def test_back_pose_already_low(self):
        """Back-facing pose: weight below max passes through."""
        assert clamp_ip_adapter_weight(0.1, "from_behind") == 0.1

    def test_side_pose_clamp(self):
        """Side-facing pose: weight clamped to 0.5."""
        assert clamp_ip_adapter_weight(0.8, "profile_standing") == 0.5

    def test_side_pose_no_clamp(self):
        """Side-facing pose: weight at max passes through."""
        assert clamp_ip_adapter_weight(0.5, "profile_standing") == 0.5

    def test_none_pose_defaults_front(self):
        """None pose defaults to front direction (no clamp)."""
        assert clamp_ip_adapter_weight(0.9, None) == 0.9

    def test_unknown_pose_defaults_front(self):
        """Unknown pose name defaults to front direction."""
        assert clamp_ip_adapter_weight(0.8, "some_unknown_pose") == 0.8

    def test_walking_is_side(self):
        """Walking is classified as side direction."""
        assert clamp_ip_adapter_weight(0.8, "walking") == 0.5


# ── _validate_controlnet_poses ───────────────────────────────────


class TestValidateControlnetPoses:
    """finalize._validate_controlnet_poses() validation."""

    def test_valid_pose_preserved(self):
        from services.agent.nodes._finalize_validators import validate_controlnet_poses as _validate_controlnet_poses

        scenes = [{"controlnet_pose": "standing"}, {"controlnet_pose": "from_behind"}]
        _validate_controlnet_poses(scenes)
        assert scenes[0]["controlnet_pose"] == "standing"
        assert scenes[1]["controlnet_pose"] == "from_behind"

    def test_invalid_pose_reset_to_none(self):
        from services.agent.nodes._finalize_validators import validate_controlnet_poses as _validate_controlnet_poses

        scenes = [{"controlnet_pose": "invalid_pose_xyz"}]
        _validate_controlnet_poses(scenes)
        assert scenes[0]["controlnet_pose"] is None

    def test_none_pose_unchanged(self):
        from services.agent.nodes._finalize_validators import validate_controlnet_poses as _validate_controlnet_poses

        scenes = [{"controlnet_pose": None}]
        _validate_controlnet_poses(scenes)
        assert scenes[0]["controlnet_pose"] is None

    def test_missing_pose_key_no_error(self):
        from services.agent.nodes._finalize_validators import validate_controlnet_poses as _validate_controlnet_poses

        scenes = [{"script": "test"}]
        _validate_controlnet_poses(scenes)
        assert "controlnet_pose" not in scenes[0]

    def test_space_format_normalized_to_underscore(self):
        """Gemini가 공백 형식으로 반환 시 언더바로 변환."""
        from services.agent.nodes._finalize_validators import validate_controlnet_poses as _validate_controlnet_poses

        scenes = [{"controlnet_pose": "from behind"}, {"controlnet_pose": "profile standing"}]
        _validate_controlnet_poses(scenes)
        assert scenes[0]["controlnet_pose"] == "from_behind"
        assert scenes[1]["controlnet_pose"] == "profile_standing"


# ── _validate_ip_adapter_weights ─────────────────────────────────


class TestValidateIpAdapterWeights:
    """finalize._validate_ip_adapter_weights() range clamping."""

    def test_valid_weight_unchanged(self):
        from services.agent.nodes._finalize_validators import (
            validate_ip_adapter_weights as _validate_ip_adapter_weights,
        )

        scenes = [{"ip_adapter_weight": 0.5}]
        _validate_ip_adapter_weights(scenes)
        assert scenes[0]["ip_adapter_weight"] == 0.5

    def test_weight_above_1_clamped(self):
        from services.agent.nodes._finalize_validators import (
            validate_ip_adapter_weights as _validate_ip_adapter_weights,
        )

        scenes = [{"ip_adapter_weight": 1.5}]
        _validate_ip_adapter_weights(scenes)
        assert scenes[0]["ip_adapter_weight"] == 1.0

    def test_negative_weight_clamped(self):
        from services.agent.nodes._finalize_validators import (
            validate_ip_adapter_weights as _validate_ip_adapter_weights,
        )

        scenes = [{"ip_adapter_weight": -0.3}]
        _validate_ip_adapter_weights(scenes)
        assert scenes[0]["ip_adapter_weight"] == 0.0

    def test_none_weight_unchanged(self):
        from services.agent.nodes._finalize_validators import (
            validate_ip_adapter_weights as _validate_ip_adapter_weights,
        )

        scenes = [{"ip_adapter_weight": None}]
        _validate_ip_adapter_weights(scenes)
        assert scenes[0]["ip_adapter_weight"] is None

    def test_missing_weight_key_no_error(self):
        from services.agent.nodes._finalize_validators import (
            validate_ip_adapter_weights as _validate_ip_adapter_weights,
        )

        scenes = [{"script": "test"}]
        _validate_ip_adapter_weights(scenes)
        assert "ip_adapter_weight" not in scenes[0]


# ── _inject_negative_prompts ───────────────────────────────────


class TestInjectNegativePrompts:
    """finalize._inject_negative_prompts() with negative_prompt_extra merging."""

    def test_default_injected_when_empty(self):
        from config import DEFAULT_SCENE_NEGATIVE_PROMPT
        from services.agent.nodes.finalize import _inject_negative_prompts

        scenes = [{"script": "test"}]
        _inject_negative_prompts(scenes)
        assert scenes[0]["negative_prompt"] == DEFAULT_SCENE_NEGATIVE_PROMPT

    def test_extra_merged_with_default(self):
        from config import DEFAULT_SCENE_NEGATIVE_PROMPT
        from services.agent.nodes.finalize import _inject_negative_prompts

        scenes = [{"negative_prompt_extra": "1girl, 1boy, person"}]
        _inject_negative_prompts(scenes)
        assert scenes[0]["negative_prompt"] == f"{DEFAULT_SCENE_NEGATIVE_PROMPT}, 1girl, 1boy, person"

    def test_no_extra_keeps_default_only(self):
        from config import DEFAULT_SCENE_NEGATIVE_PROMPT
        from services.agent.nodes.finalize import _inject_negative_prompts

        scenes = [{"negative_prompt_extra": ""}]
        _inject_negative_prompts(scenes)
        assert scenes[0]["negative_prompt"] == DEFAULT_SCENE_NEGATIVE_PROMPT

    def test_existing_negative_prompt_preserved(self):
        from services.agent.nodes.finalize import _inject_negative_prompts

        scenes = [{"negative_prompt": "custom_negative", "negative_prompt_extra": "outdoors"}]
        _inject_negative_prompts(scenes)
        assert scenes[0]["negative_prompt"] == "custom_negative, outdoors"

    def test_existing_negative_prompt_no_extra(self):
        from services.agent.nodes.finalize import _inject_negative_prompts

        scenes = [{"negative_prompt": "custom_negative"}]
        _inject_negative_prompts(scenes)
        assert scenes[0]["negative_prompt"] == "custom_negative"


# ── _normalize_environment_tags ────────────────────────────────


class TestNormalizeEnvironmentTags:
    """finalize._normalize_environment_tags() setting→environment conversion."""

    def test_setting_converted_to_environment(self):
        from services.agent.nodes.finalize import _normalize_environment_tags

        scenes = [{"context_tags": {"setting": "kitchen", "mood": "dark"}}]
        _normalize_environment_tags(scenes)
        assert scenes[0]["context_tags"]["environment"] == "kitchen"
        assert "setting" not in scenes[0]["context_tags"]

    def test_environment_already_exists_not_overwritten(self):
        from services.agent.nodes.finalize import _normalize_environment_tags

        scenes = [{"context_tags": {"setting": "kitchen", "environment": "outdoor_garden"}}]
        _normalize_environment_tags(scenes)
        assert scenes[0]["context_tags"]["environment"] == "outdoor_garden"
        assert scenes[0]["context_tags"]["setting"] == "kitchen"

    def test_no_context_tags_no_error(self):
        from services.agent.nodes.finalize import _normalize_environment_tags

        scenes = [{"script": "test"}]
        _normalize_environment_tags(scenes)
        assert "context_tags" not in scenes[0]

    def test_empty_context_tags_no_error(self):
        from services.agent.nodes.finalize import _normalize_environment_tags

        scenes = [{"context_tags": {}}]
        _normalize_environment_tags(scenes)
        assert scenes[0]["context_tags"] == {}

    def test_neither_setting_nor_environment(self):
        from services.agent.nodes.finalize import _normalize_environment_tags

        scenes = [{"context_tags": {"pose": "standing", "gaze": "looking_down"}}]
        _normalize_environment_tags(scenes)
        assert "environment" not in scenes[0]["context_tags"]
        assert "setting" not in scenes[0]["context_tags"]
