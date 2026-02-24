"""Tests for finalize.py: quality 태그 정화 + emotion 인식 기본값."""

from services.agent.nodes.finalize import (
    _inject_default_context_tags,
    _sanitize_quality_tags,
)

# ── _sanitize_quality_tags ────────────────────────────────────────────


class TestSanitizeQualityTags:
    """비표준 quality 태그 치환 테스트."""

    def test_high_quality_replaced(self):
        scenes = [{"image_prompt": "masterpiece, high_quality, 1girl"}]
        _sanitize_quality_tags(scenes)
        assert scenes[0]["image_prompt"] == "masterpiece, best_quality, 1girl"

    def test_no_change_when_clean(self):
        scenes = [{"image_prompt": "masterpiece, best_quality, 1girl"}]
        _sanitize_quality_tags(scenes)
        assert scenes[0]["image_prompt"] == "masterpiece, best_quality, 1girl"

    def test_empty_prompt_skipped(self):
        scenes = [{"image_prompt": ""}]
        _sanitize_quality_tags(scenes)
        assert scenes[0]["image_prompt"] == ""

    def test_missing_prompt_skipped(self):
        scenes = [{"speaker": "Narrator"}]
        _sanitize_quality_tags(scenes)
        assert "image_prompt" not in scenes[0]

    def test_multiple_scenes(self):
        scenes = [
            {"image_prompt": "high_quality, smile"},
            {"image_prompt": "masterpiece, detailed"},
        ]
        _sanitize_quality_tags(scenes)
        assert scenes[0]["image_prompt"] == "best_quality, smile"
        assert scenes[1]["image_prompt"] == "masterpiece, detailed"


# ── _inject_default_context_tags with emotion ─────────────────────────


class TestInjectDefaultContextTagsEmotion:
    """emotion 기반 expression 파생 테스트."""

    def test_emotion_derives_expression(self):
        """emotion='sad'이면 expression='sad' 파생."""
        scenes = [
            {"speaker": "Character", "context_tags": {"emotion": "sad", "pose": "standing", "gaze": "looking_down"}}
        ]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["expression"] == "sad"

    def test_emotion_angry_derives_angry(self):
        scenes = [{"speaker": "A", "context_tags": {"emotion": "angry"}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["expression"] == "angry"

    def test_existing_expression_not_overridden(self):
        """expression이 이미 있으면 emotion 무시."""
        scenes = [{"speaker": "A", "context_tags": {"emotion": "angry", "expression": "smile"}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["expression"] == "smile"

    def test_unknown_emotion_fallback_to_default(self):
        """알 수 없는 emotion이면 기본값 사용."""
        scenes = [{"speaker": "A", "context_tags": {"emotion": "mysterious_feeling"}}]
        _inject_default_context_tags(scenes)
        # DEFAULT_EXPRESSION_TAG = "smile"
        assert scenes[0]["context_tags"]["expression"] == "smile"

    def test_no_emotion_uses_default(self):
        """emotion 없으면 기본값."""
        scenes = [{"speaker": "A", "context_tags": {}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["expression"] == "smile"

    def test_narrator_skipped(self):
        scenes = [{"speaker": "Narrator", "context_tags": {}}]
        _inject_default_context_tags(scenes)
        assert "expression" not in scenes[0]["context_tags"]

    def test_list_emotion_coerced(self):
        """Gemini가 emotion을 리스트로 반환한 경우 방어."""
        scenes = [{"speaker": "A", "context_tags": {"emotion": ["sad"]}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["expression"] == "sad"
