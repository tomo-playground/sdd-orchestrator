"""Tests for _context_tag_utils: emotion→expression 매핑, 카테고리 검증, 카메라 다양성."""

import logging

import pytest

from services.agent.nodes._context_tag_utils import (
    EMOTION_TO_EXPRESSION,
    check_camera_diversity,
    derive_expression_from_emotion,
    validate_context_tag_categories,
)

# ── derive_expression_from_emotion ────────────────────────────────────


class TestDeriveExpression:
    """emotion → expression 매핑 테스트."""

    @pytest.mark.parametrize(
        "emotion,expected",
        [
            ("happy", "smile"),
            ("sad", "sad"),
            ("angry", "angry"),
            ("surprised", "surprised"),
            ("calm", "expressionless"),
            ("determined", "serious"),
            ("embarrassed", "embarrassed"),
            ("sleepy", "sleepy"),
            ("hopeful", "smile"),
            ("grieving", "crying"),
        ],
    )
    def test_known_emotions(self, emotion: str, expected: str):
        assert derive_expression_from_emotion(emotion) == expected

    def test_case_insensitive(self):
        assert derive_expression_from_emotion("HAPPY") == "smile"
        assert derive_expression_from_emotion(" Sad ") == "sad"

    def test_unknown_returns_none(self):
        assert derive_expression_from_emotion("unknown_emotion") is None
        assert derive_expression_from_emotion("") is None

    def test_list_input_coerced(self):
        """Gemini가 리스트로 반환한 경우 첫 번째 요소 사용."""
        assert derive_expression_from_emotion(["sad"]) == "sad"
        assert derive_expression_from_emotion(["angry", "frustrated"]) == "angry"

    def test_none_input(self):
        assert derive_expression_from_emotion(None) is None

    def test_all_values_are_strings(self):
        for k, v in EMOTION_TO_EXPRESSION.items():
            assert isinstance(k, str) and isinstance(v, str)


# ── validate_context_tag_categories ───────────────────────────────────


class TestValidateContextTagCategories:
    """카테고리 검증 + 재분류 테스트."""

    def test_valid_tags_unchanged(self):
        scenes = [{"context_tags": {"expression": "smile", "gaze": "looking_at_viewer", "pose": "standing"}}]
        validate_context_tag_categories(scenes)
        ctx = scenes[0]["context_tags"]
        assert ctx["expression"] == "smile"
        assert ctx["gaze"] == "looking_at_viewer"
        assert ctx["pose"] == "standing"

    def test_misplaced_gaze_to_expression(self):
        """gaze="crying"은 expression으로 재분류."""
        scenes = [{"context_tags": {"expression": "", "gaze": "crying", "pose": "standing"}}]
        validate_context_tag_categories(scenes)
        ctx = scenes[0]["context_tags"]
        assert ctx["expression"] == "crying"
        assert ctx["gaze"] == ""

    def test_invalid_mood_dropped(self, caplog):
        """비표준 mood('clay_look')은 drop."""
        scenes = [{"context_tags": {"mood": "clay_look"}}]
        with caplog.at_level(logging.WARNING):
            validate_context_tag_categories(scenes)
        assert scenes[0]["context_tags"]["mood"] == ""
        assert "비표준 mood" in caplog.text

    def test_valid_mood_preserved(self):
        scenes = [{"context_tags": {"mood": "romantic"}}]
        validate_context_tag_categories(scenes)
        assert scenes[0]["context_tags"]["mood"] == "romantic"

    def test_no_context_tags_skipped(self):
        scenes = [{"speaker": "Narrator"}]
        validate_context_tag_categories(scenes)  # no error

    def test_list_values_coerced(self):
        """Gemini가 리스트로 반환한 context_tags 값 방어."""
        scenes = [{"context_tags": {"expression": ["smile"], "gaze": ["looking_at_viewer"], "pose": "standing"}}]
        validate_context_tag_categories(scenes)
        ctx = scenes[0]["context_tags"]
        assert ctx["expression"] == "smile"
        assert ctx["gaze"] == "looking_at_viewer"

    def test_list_mood_coerced(self, caplog):
        scenes = [{"context_tags": {"mood": ["clay_look"]}}]
        with caplog.at_level(logging.WARNING):
            validate_context_tag_categories(scenes)
        assert scenes[0]["context_tags"]["mood"] == ""


# ── check_camera_diversity ────────────────────────────────────────────


class TestCheckCameraDiversity:
    """카메라 다양성 소프트 경고 테스트."""

    def test_diverse_no_warning(self, caplog):
        scenes = [
            {"context_tags": {"camera": "close-up"}},
            {"context_tags": {"camera": "medium_shot"}},
            {"context_tags": {"camera": "wide_shot"}},
        ]
        with caplog.at_level(logging.WARNING):
            check_camera_diversity(scenes)
        assert "카메라 다양성 부족" not in caplog.text

    def test_repetitive_warns(self, caplog):
        scenes = [
            {"context_tags": {"camera": "close-up"}},
            {"context_tags": {"camera": "close-up"}},
            {"context_tags": {"camera": "close-up"}},
        ]
        with caplog.at_level(logging.WARNING):
            check_camera_diversity(scenes)
        assert "카메라 다양성 부족" in caplog.text

    def test_less_than_3_scenes_no_check(self, caplog):
        scenes = [{"context_tags": {"camera": "close-up"}}, {"context_tags": {"camera": "close-up"}}]
        with caplog.at_level(logging.WARNING):
            check_camera_diversity(scenes)
        assert "카메라 다양성 부족" not in caplog.text
