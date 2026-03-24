"""context_tags 구조화: cross-field 검증 + image_prompt 재조립 테스트."""

from __future__ import annotations

from services.agent.nodes.finalize import (
    _has_crowd_indicators,
    _rebuild_image_prompt_from_context_tags,
    _validate_cross_field_consistency,
)

# ── cross-field validation ──────────────────────────────


class TestCrossFieldConsistency:
    def test_from_behind_looking_at_viewer(self):
        scenes = [{"context_tags": {"camera": "from_behind", "gaze": "looking_at_viewer"}}]
        _validate_cross_field_consistency(scenes)
        assert scenes[0]["context_tags"]["gaze"] == "looking_back"

    def test_from_below_looking_down(self):
        scenes = [{"context_tags": {"camera": "from_below", "gaze": "looking_down"}}]
        _validate_cross_field_consistency(scenes)
        assert scenes[0]["context_tags"]["gaze"] == "looking_up"

    def test_from_above_looking_up(self):
        scenes = [{"context_tags": {"camera": "from_above", "gaze": "looking_up"}}]
        _validate_cross_field_consistency(scenes)
        assert scenes[0]["context_tags"]["gaze"] == "looking_down"

    def test_no_conflict_unchanged(self):
        scenes = [{"context_tags": {"camera": "close-up", "gaze": "looking_at_viewer"}}]
        _validate_cross_field_consistency(scenes)
        assert scenes[0]["context_tags"]["gaze"] == "looking_at_viewer"

    def test_no_context_tags_skip(self):
        scenes = [{"speaker": "speaker_1"}]
        _validate_cross_field_consistency(scenes)
        assert "context_tags" not in scenes[0]

    def test_empty_camera_gaze_skip(self):
        scenes = [{"context_tags": {"emotion": "happy"}}]
        _validate_cross_field_consistency(scenes)
        assert "gaze" not in scenes[0]["context_tags"]


# ── image_prompt rebuild ────────────────────────────────


class TestRebuildImagePrompt:
    def test_character_scene_full(self):
        scenes = [
            {
                "speaker": "speaker_1",
                "camera": "cowboy_shot",
                "context_tags": {
                    "emotion": "nervous",
                    "camera": "close-up",
                    "action": "holding_knife",
                    "pose": "standing",
                    "gaze": "looking_down",
                    "expression": "nervous",
                    "environment": ["kitchen", "indoors"],
                    "cinematic": ["depth_of_field"],
                    "props": ["knife"],
                },
            }
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        prompt = scenes[0]["image_prompt"]
        tags = [t.strip() for t in prompt.split(",")]
        # camera first
        assert tags[0] == "close-up"
        # pose + gaze early
        assert "standing" in tags
        assert "looking_down" in tags
        # action + props
        assert "holding_knife" in tags
        assert "knife" in tags
        # expression
        assert "nervous" in tags
        # environment
        assert "kitchen" in tags
        assert "indoors" in tags
        # cinematic last
        assert "depth_of_field" in tags

    def test_narrator_scene(self):
        scenes = [
            {
                "speaker": "narrator",
                "context_tags": {
                    "camera": "from_above",
                    "environment": ["hallway", "indoors", "night"],
                    "cinematic": ["moonlight"],
                    "props": ["door"],
                },
            }
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        prompt = scenes[0]["image_prompt"]
        tags = [t.strip() for t in prompt.split(",")]
        # narrator prefixes
        assert tags[0] == "no_humans"
        assert tags[1] == "scenery"
        # no pose/gaze for narrator
        assert "standing" not in tags
        # environment + cinematic
        assert "hallway" in tags
        assert "moonlight" in tags

    def test_rebuilds_when_standard_fields_present(self):
        """B-1: cinematic/props 없어도 action/environment 등 표준 필드가 있으면 재조립."""
        scenes = [
            {
                "speaker": "speaker_1",
                "image_prompt": "nervous, holding_knife, white_shirt, kitchen",
                "context_tags": {
                    "emotion": "nervous",  # _CONTEXT_TAG_FIELDS 아님 → 무시
                    "action": "holding_knife",  # _CONTEXT_TAG_FIELDS → 재조립
                    "environment": ["kitchen"],
                },
            }
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        prompt = scenes[0]["image_prompt"]
        # 재조립 → action + environment만 포함, white_shirt(복장 오염) 제거됨
        assert "holding_knife" in prompt
        assert "kitchen" in prompt
        assert "white_shirt" not in prompt

    def test_skip_no_context_tags(self):
        original_prompt = "some_tag, another_tag"
        scenes = [{"speaker": "speaker_1", "image_prompt": original_prompt}]
        _rebuild_image_prompt_from_context_tags(scenes)
        assert scenes[0]["image_prompt"] == original_prompt

    def test_env_string_not_list(self):
        """environment가 문자열인 경우도 처리."""
        scenes = [
            {
                "speaker": "speaker_1",
                "context_tags": {
                    "camera": "close-up",
                    "environment": "kitchen",
                    "cinematic": ["backlighting"],
                },
            }
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        assert "kitchen" in scenes[0]["image_prompt"]
        assert "backlighting" in scenes[0]["image_prompt"]

    def test_camera_fallback_to_scene_level(self):
        """context_tags.camera 없으면 scene['camera'] 사용."""
        scenes = [
            {
                "speaker": "speaker_1",
                "camera": "cowboy_shot",
                "context_tags": {
                    "action": "walking",
                    "cinematic": ["sunlight"],
                },
            }
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        assert "cowboy_shot" in scenes[0]["image_prompt"]

    def test_multiple_scenes_both_rebuild(self):
        """B-1: 두 씬 모두 표준 필드 있으면 각각 재조립."""
        scenes = [
            {
                "speaker": "speaker_1",
                "image_prompt": "old_prompt, blue_skirt",
                "context_tags": {"emotion": "happy", "action": "smile"},
            },
            {
                "speaker": "speaker_1",
                "image_prompt": "old_prompt_2",
                "context_tags": {
                    "camera": "close-up",
                    "action": "crying",
                    "cinematic": ["depth_of_field"],
                },
            },
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        # 씬 0: action="smile" → 재조립, blue_skirt(복장 오염) 제거
        assert "smile" in scenes[0]["image_prompt"]
        assert "blue_skirt" not in scenes[0]["image_prompt"]
        # 씬 1: 재조립
        assert "crying" in scenes[1]["image_prompt"]

    def test_empty_props_and_cinematic_but_action_present(self):
        """B-1: cinematic/props 빈 배열이어도 action이 있으면 재조립."""
        scenes = [
            {
                "speaker": "speaker_1",
                "image_prompt": "some_tags, red_dress",
                "context_tags": {
                    "action": "walking",
                    "cinematic": [],
                    "props": [],
                },
            }
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        # action="walking" → 재조립, red_dress 제거
        assert "walking" in scenes[0]["image_prompt"]
        assert "red_dress" not in scenes[0]["image_prompt"]

    def test_skip_completely_empty_context_tags(self):
        """context_tags가 완전히 빈 dict이면 skip (구 스토리보드 후방 호환)."""
        original = "some_tags, white_shirt"
        scenes = [{"speaker": "speaker_1", "image_prompt": original, "context_tags": {}}]
        _rebuild_image_prompt_from_context_tags(scenes)
        assert scenes[0]["image_prompt"] == original


# ── crowd narrator (SP-072) ───────────────────────────


class TestHasCrowdIndicators:
    """_has_crowd_indicators 헬퍼 검증."""

    def test_crowd_in_image_prompt(self):
        scene = {"image_prompt": "scenery, crowd, busy_street"}
        assert _has_crowd_indicators(scene) is True

    def test_many_others_in_image_prompt(self):
        scene = {"image_prompt": "scenery, many_others, office"}
        assert _has_crowd_indicators(scene) is True

    def test_crowd_in_context_tags_action(self):
        scene = {"image_prompt": "scenery", "context_tags": {"action": "crowd"}}
        assert _has_crowd_indicators(scene) is True

    def test_crowd_in_context_tags_environment_list(self):
        scene = {"image_prompt": "scenery", "context_tags": {"environment": ["crowd", "street"]}}
        assert _has_crowd_indicators(scene) is True

    def test_no_crowd_returns_false(self):
        scene = {"image_prompt": "scenery, empty_room", "context_tags": {"environment": ["hallway"]}}
        assert _has_crowd_indicators(scene) is False

    def test_empty_scene(self):
        scene = {"image_prompt": ""}
        assert _has_crowd_indicators(scene) is False


class TestNarratorCrowdRebuild:
    """Narrator + 군중 씬에서 no_humans 스킵 검증."""

    def test_narrator_crowd_skips_no_humans_in_rebuild(self):
        """Narrator + crowd in image_prompt → rebuild 시 no_humans 없음, scenery 있음."""
        scenes = [
            {
                "speaker": "narrator",
                "image_prompt": "crowd, busy_street, scenery",
                "context_tags": {
                    "camera": "wide_shot",
                    "environment": ["busy_street"],
                },
            }
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        prompt = scenes[0]["image_prompt"]
        tags = [t.strip() for t in prompt.split(",")]
        assert "no_humans" not in tags
        assert "scenery" in tags

    def test_narrator_empty_keeps_no_humans_in_rebuild(self):
        """Narrator + 빈 공간 → no_humans, scenery 유지 (regression guard)."""
        scenes = [
            {
                "speaker": "narrator",
                "image_prompt": "empty_classroom, scenery",
                "context_tags": {
                    "camera": "wide_shot",
                    "environment": ["empty_classroom"],
                },
            }
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        prompt = scenes[0]["image_prompt"]
        tags = [t.strip() for t in prompt.split(",")]
        assert "no_humans" in tags
        assert "scenery" in tags
