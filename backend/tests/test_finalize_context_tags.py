"""context_tags 구조화: cross-field 검증 + image_prompt 재조립 테스트."""

from __future__ import annotations

from services.agent.nodes.finalize import (
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
        scenes = [{"speaker": "A"}]
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
                "speaker": "A",
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
                "speaker": "Narrator",
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

    def test_skip_old_format_no_cinematic_no_props(self):
        """확장 필드 없는 기존 스토리보드는 건너뛴다."""
        original_prompt = "nervous, holding_knife, kitchen"
        scenes = [
            {
                "speaker": "A",
                "image_prompt": original_prompt,
                "context_tags": {
                    "emotion": "nervous",
                    "action": "holding_knife",
                    "environment": ["kitchen"],
                },
            }
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        assert scenes[0]["image_prompt"] == original_prompt

    def test_skip_no_context_tags(self):
        original_prompt = "some_tag, another_tag"
        scenes = [{"speaker": "A", "image_prompt": original_prompt}]
        _rebuild_image_prompt_from_context_tags(scenes)
        assert scenes[0]["image_prompt"] == original_prompt

    def test_env_string_not_list(self):
        """environment가 문자열인 경우도 처리."""
        scenes = [
            {
                "speaker": "A",
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
                "speaker": "A",
                "camera": "cowboy_shot",
                "context_tags": {
                    "action": "walking",
                    "cinematic": ["sunlight"],
                },
            }
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        assert "cowboy_shot" in scenes[0]["image_prompt"]

    def test_multiple_scenes_partial_rebuild(self):
        """확장 형식 씬만 재조립, 나머지는 유지."""
        scenes = [
            {
                "speaker": "A",
                "image_prompt": "old_prompt",
                "context_tags": {"emotion": "happy", "action": "smile"},
            },
            {
                "speaker": "A",
                "image_prompt": "old_prompt_2",
                "context_tags": {
                    "camera": "close-up",
                    "action": "crying",
                    "cinematic": ["depth_of_field"],
                },
            },
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        assert scenes[0]["image_prompt"] == "old_prompt"  # no cinematic/props → skip
        assert "crying" in scenes[1]["image_prompt"]  # rebuilt

    def test_empty_props_and_cinematic(self):
        """빈 배열이면 cinematic/props 존재로 간주하지 않음."""
        original = "some_tags"
        scenes = [
            {
                "speaker": "A",
                "image_prompt": original,
                "context_tags": {
                    "action": "walking",
                    "cinematic": [],
                    "props": [],
                },
            }
        ]
        _rebuild_image_prompt_from_context_tags(scenes)
        assert scenes[0]["image_prompt"] == original
