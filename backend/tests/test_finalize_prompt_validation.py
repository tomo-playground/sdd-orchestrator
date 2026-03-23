"""Finalize L2 검증: 금지 태그 필터 + Danbooru 형식 정규화 + context_tags 유효성 + sanity check."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.agent.nodes.finalize import (
    _filter_prohibited_tags,
    _normalize_danbooru_format,
    _normalize_single_token,
    _validate_context_tag_values,
    _validate_final_image_prompt,
)

# ── DoD 1: 금지 태그 필터 ─────────────────────────────────────────────


class TestFilterProhibitedTags:
    def test_removes_known_forbidden(self):
        scenes = [{"image_prompt": "cowboy_shot, cinematic_shadows, smile, medium_shot"}]
        _filter_prohibited_tags(scenes)
        assert scenes[0]["image_prompt"] == "cowboy_shot, smile"

    def test_preserves_valid_tags(self):
        scenes = [{"image_prompt": "cowboy_shot, smile, brown_hair"}]
        _filter_prohibited_tags(scenes)
        assert scenes[0]["image_prompt"] == "cowboy_shot, smile, brown_hair"

    def test_removes_weighted_prohibited(self):
        scenes = [{"image_prompt": "(cinematic_shadows:1.2), smile"}]
        _filter_prohibited_tags(scenes)
        assert scenes[0]["image_prompt"] == "smile"

    def test_empty_prompt_skipped(self):
        scenes = [{"image_prompt": ""}, {"image_prompt": None}]
        _filter_prohibited_tags(scenes)
        assert scenes[0]["image_prompt"] == ""
        assert scenes[1]["image_prompt"] is None

    def test_similar_valid_preserved(self):
        """high_contrast는 유효, high_contrast_shadow만 금지."""
        scenes = [{"image_prompt": "high_contrast, high_contrast_shadow"}]
        _filter_prohibited_tags(scenes)
        assert scenes[0]["image_prompt"] == "high_contrast"

    def test_removes_emotion_adjectives(self):
        scenes = [{"image_prompt": "smile, confident, looking_at_viewer"}]
        _filter_prohibited_tags(scenes)
        assert scenes[0]["image_prompt"] == "smile, looking_at_viewer"

    def test_removes_gender_tags(self):
        scenes = [{"image_prompt": "1girl, female, cowboy_shot"}]
        _filter_prohibited_tags(scenes)
        assert scenes[0]["image_prompt"] == "1girl, cowboy_shot"


# ── DoD 2: Danbooru 형식 정규화 ───────────────────────────────────────


class TestNormalizeDanbooruFormat:
    def test_spaces_to_underscores(self):
        scenes = [{"image_prompt": "blue eyes, brown hair"}]
        _normalize_danbooru_format(scenes)
        assert scenes[0]["image_prompt"] == "blue_eyes, brown_hair"

    def test_preserves_hyphens(self):
        scenes = [{"image_prompt": "close-up, half-closed_eyes"}]
        _normalize_danbooru_format(scenes)
        assert scenes[0]["image_prompt"] == "close-up, half-closed_eyes"

    def test_preserves_lora_tags(self):
        scenes = [{"image_prompt": "<lora:style_xl:0.8>, blue eyes"}]
        _normalize_danbooru_format(scenes)
        assert "<lora:style_xl:0.8>" in scenes[0]["image_prompt"]
        assert "blue_eyes" in scenes[0]["image_prompt"]

    def test_weight_syntax_normalized(self):
        scenes = [{"image_prompt": "(blue eyes:1.3)"}]
        _normalize_danbooru_format(scenes)
        assert scenes[0]["image_prompt"] == "(blue_eyes:1.3)"

    def test_empty_prompt_skipped(self):
        scenes = [{"image_prompt": ""}]
        _normalize_danbooru_format(scenes)
        assert scenes[0]["image_prompt"] == ""


class TestNormalizeSingleToken:
    def test_lora_trigger_preserved(self):
        """LoRA 트리거 워드는 공백이 있어도 원본 유지."""
        mock_cache = MagicMock()
        mock_cache.get_lora_name.return_value = "style_lora"
        token = "flat color"
        result = _normalize_single_token(token, mock_cache)
        assert result == "flat color"

    def test_regular_token_normalized(self):
        mock_cache = MagicMock()
        mock_cache.get_lora_name.return_value = None
        result = _normalize_single_token("blue eyes", mock_cache)
        assert result == "blue_eyes"

    def test_lora_tag_passthrough(self):
        mock_cache = MagicMock()
        result = _normalize_single_token("<lora:style_xl:0.8>", mock_cache)
        assert result == "<lora:style_xl:0.8>"
        mock_cache.get_lora_name.assert_not_called()


# ── DoD 3: context_tags 유효성 검증 ───────────────────────────────────


class TestValidateContextTagValues:
    def test_emotion_valid_unchanged(self):
        scenes = [{"context_tags": {"emotion": "happy"}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["emotion"] == "happy"

    def test_emotion_korean_normalized(self):
        scenes = [{"context_tags": {"emotion": "기쁨"}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["emotion"] == "happy"

    def test_emotion_invalid_fallback(self):
        from config import DEFAULT_EMOTION_TAG

        scenes = [{"context_tags": {"emotion": "perplexed"}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["emotion"] == DEFAULT_EMOTION_TAG

    def test_emotion_compound_normalized(self):
        scenes = [{"context_tags": {"emotion": "lonely_expression"}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["emotion"] == "lonely"

    def test_camera_valid_unchanged(self):
        scenes = [{"context_tags": {"camera": "cowboy_shot"}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["camera"] == "cowboy_shot"

    def test_camera_space_normalized(self):
        scenes = [{"context_tags": {"camera": "cowboy shot"}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["camera"] == "cowboy_shot"

    def test_camera_invalid_fallback(self):
        from config import DEFAULT_CAMERA_TAG

        scenes = [{"context_tags": {"camera": "medium_shot"}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["camera"] == DEFAULT_CAMERA_TAG

    def test_camera_list_picks_first_valid(self):
        scenes = [{"context_tags": {"camera": ["medium_shot", "cowboy_shot"]}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["camera"] == "cowboy_shot"

    def test_camera_list_all_invalid_fallback(self):
        from config import DEFAULT_CAMERA_TAG

        scenes = [{"context_tags": {"camera": ["medium_shot", "invalid_cam"]}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["camera"] == DEFAULT_CAMERA_TAG

    def test_gaze_valid_unchanged(self):
        scenes = [{"context_tags": {"gaze": "looking_down"}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["gaze"] == "looking_down"

    def test_gaze_alias_applied(self):
        scenes = [{"context_tags": {"gaze": "looking_at_another"}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["gaze"] == "looking_to_the_side"

    def test_gaze_invalid_fallback(self):
        from config import DEFAULT_GAZE_TAG

        scenes = [{"context_tags": {"gaze": "staring_into_space"}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["gaze"] == DEFAULT_GAZE_TAG

    def test_narrator_camera_validated(self):
        from config import DEFAULT_CAMERA_TAG

        scenes = [{"speaker": "Narrator", "context_tags": {"camera": "medium_shot"}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["camera"] == DEFAULT_CAMERA_TAG

    def test_no_context_tags_skip(self):
        scenes = [{"speaker": "A"}]
        _validate_context_tag_values(scenes)
        assert "context_tags" not in scenes[0]

    def test_emotion_list_coerced(self):
        scenes = [{"context_tags": {"emotion": ["happy", "sad"]}}]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["emotion"] == "happy"


# ── DoD 4: 재조립 후 sanity check ─────────────────────────────────────


class TestValidateFinalImagePrompt:
    def test_narrator_empty_fallback(self):
        from config import NARRATOR_FALLBACK_PROMPT

        scenes = [{"speaker": "Narrator", "image_prompt": ""}]
        _validate_final_image_prompt(scenes)
        assert scenes[0]["image_prompt"] == NARRATOR_FALLBACK_PROMPT

    def test_character_empty_warning(self):
        scenes = [{"speaker": "A", "image_prompt": ""}]
        _validate_final_image_prompt(scenes)
        assert scenes[0]["image_prompt"] == ""

    def test_double_comma_cleanup(self):
        scenes = [{"speaker": "A", "image_prompt": "tag_a,, tag_b, , tag_c"}]
        _validate_final_image_prompt(scenes)
        assert scenes[0]["image_prompt"] == "tag_a, tag_b, tag_c"

    def test_tag_count_over_50_truncated(self):
        tags = [f"tag_{i}" for i in range(60)]
        scenes = [{"speaker": "A", "image_prompt": ", ".join(tags)}]
        _validate_final_image_prompt(scenes)
        result_tags = scenes[0]["image_prompt"].split(", ")
        assert len(result_tags) == 50

    def test_tag_count_under_50_unchanged(self):
        tags = [f"tag_{i}" for i in range(30)]
        prompt = ", ".join(tags)
        scenes = [{"speaker": "A", "image_prompt": prompt}]
        _validate_final_image_prompt(scenes)
        assert len(scenes[0]["image_prompt"].split(", ")) == 30

    def test_incomplete_weight_removed(self):
        scenes = [{"speaker": "A", "image_prompt": "(tag:), (:1.2), valid_tag"}]
        _validate_final_image_prompt(scenes)
        assert "valid_tag" in scenes[0]["image_prompt"]
        assert "(tag:)" not in scenes[0]["image_prompt"]
        assert "(:1.2)" not in scenes[0]["image_prompt"]

    def test_valid_weight_preserved(self):
        scenes = [{"speaker": "A", "image_prompt": "(tag:1.2), ((emphasis))"}]
        _validate_final_image_prompt(scenes)
        assert "(tag:1.2)" in scenes[0]["image_prompt"]
        assert "((emphasis))" in scenes[0]["image_prompt"]

    def test_unmatched_open_paren_removed(self):
        scenes = [{"speaker": "A", "image_prompt": "tag_a, orphan_paren(, tag_b"}]
        _validate_final_image_prompt(scenes)
        result = scenes[0]["image_prompt"]
        assert result.count("(") == result.count(")")
        assert "tag_a" in result
        assert "tag_b" in result

    def test_narrator_empty_after_cleanup_gets_fallback(self):
        from config import NARRATOR_FALLBACK_PROMPT

        scenes = [{"speaker": "Narrator", "image_prompt": ",,, ,, "}]
        _validate_final_image_prompt(scenes)
        assert scenes[0]["image_prompt"] == NARRATOR_FALLBACK_PROMPT

    def test_narrator_malformed_weight_only_gets_fallback(self):
        """malformed weight 구문만 있는 Narrator prompt -> 정리 후 fallback 주입."""
        from config import NARRATOR_FALLBACK_PROMPT

        scenes = [{"speaker": "Narrator", "image_prompt": "(tag:), (:1.2)"}]
        _validate_final_image_prompt(scenes)
        assert scenes[0]["image_prompt"] == NARRATOR_FALLBACK_PROMPT
