"""Tests for _context_tag_utils: emotion→expression 매핑, 카테고리 검증, 카메라 다양성."""

import logging

import pytest

from services.agent.nodes._context_tag_utils import (
    EMOTION_TO_EXPRESSION,
    derive_expression_from_emotion,
    validate_context_tag_categories,
)
from services.agent.nodes._diversify_utils import diversify_cameras

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
            ("tired", "half-closed_eyes"),
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
        assert "gaze" not in ctx  # 잘못 분류된 필드는 키 삭제

    def test_invalid_mood_dropped(self, caplog):
        """비표준 mood('clay_look')은 drop."""
        scenes = [{"context_tags": {"mood": "clay_look"}}]
        with caplog.at_level(logging.WARNING):
            validate_context_tag_categories(scenes)
        assert "mood" not in scenes[0]["context_tags"]  # 키 삭제
        assert "비표준 mood" in caplog.text

    def test_valid_mood_preserved(self):
        scenes = [{"context_tags": {"mood": "romantic"}}]
        validate_context_tag_categories(scenes)
        assert scenes[0]["context_tags"]["mood"] == "romantic"

    def test_no_context_tags_skipped(self):
        scenes = [{"speaker": "narrator"}]
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
        assert "mood" not in scenes[0]["context_tags"]  # 키 삭제


# ── diversify_cameras ────────────────────────────────────────────


class TestDiversifyCamerasUnit:
    """카메라 다양성 보정 단위 테스트."""

    def test_diverse_no_change(self, caplog):
        scenes = [
            {"context_tags": {"camera": "close-up", "emotion": "sad"}},
            {"context_tags": {"camera": "cowboy_shot", "emotion": "happy"}},
            {"context_tags": {"camera": "full_body", "emotion": "angry"}},
        ]
        with caplog.at_level(logging.INFO):
            diversify_cameras(scenes)
        assert "Camera 단조로움 감지" not in caplog.text

    def test_repetitive_corrected(self, caplog):
        scenes = [
            {"context_tags": {"camera": "close-up", "emotion": "happy"}},
            {"context_tags": {"camera": "close-up", "emotion": "angry"}},
            {"context_tags": {"camera": "close-up", "emotion": "sad"}},
        ]
        with caplog.at_level(logging.INFO):
            diversify_cameras(scenes)
        assert "Camera 단조로움 감지" in caplog.text

    def test_less_than_3_scenes_no_check(self, caplog):
        scenes = [
            {"context_tags": {"camera": "close-up", "emotion": "sad"}},
            {"context_tags": {"camera": "close-up", "emotion": "happy"}},
        ]
        with caplog.at_level(logging.INFO):
            diversify_cameras(scenes)
        assert "Camera 단조로움 감지" not in caplog.text
