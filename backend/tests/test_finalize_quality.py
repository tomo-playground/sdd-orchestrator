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

    def test_emotion_overrides_existing_expression(self):
        """emotion이 매핑되면 기존 expression을 오버라이드 (monotony 방지)."""
        scenes = [{"speaker": "A", "context_tags": {"emotion": "angry", "expression": "smile"}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["expression"] == "angry"

    def test_unmapped_emotion_keeps_existing_expression(self):
        """emotion이 매핑 안 되면 기존 expression 유지."""
        scenes = [{"speaker": "A", "context_tags": {"emotion": "mysterious_vibe", "expression": "smile"}}]
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

    def test_mood_derived_from_emotion(self):
        """emotion에서 mood 자동 파생."""
        scenes = [{"speaker": "A", "context_tags": {"emotion": "소외감"}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["mood"] == "lonely"

    def test_mood_not_overridden_if_exists(self):
        """기존 mood 유지."""
        scenes = [{"speaker": "A", "context_tags": {"emotion": "sad", "mood": "tense"}}]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["mood"] == "tense"

    def test_korean_compound_emotion_derives_expression(self):
        """복합 한국어 emotion → expression 파생."""
        scenes = [
            {"speaker": "A", "context_tags": {"emotion": "공감 유도"}},
            {"speaker": "A", "context_tags": {"emotion": "내적 갈등"}},
            {"speaker": "A", "context_tags": {"emotion": "체념"}},
        ]
        _inject_default_context_tags(scenes)
        assert scenes[0]["context_tags"]["expression"] == "smile"
        assert scenes[1]["context_tags"]["expression"] == "serious"  # 내적 갈등 → tense → serious
        assert scenes[2]["context_tags"]["expression"] == "expressionless"
