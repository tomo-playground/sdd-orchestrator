"""Test: Finalize 감정 중복 연속 검증 (A-1).

_validate_emotion_continuity() 순수 함수 단위 테스트.
"""

from __future__ import annotations

import logging


class TestValidateEmotionContinuity:
    """A-1: 동일 speaker 연속 씬 감정 중복 → WARNING/ERROR 로그."""

    def _call(self, scenes):
        from services.agent.nodes.finalize import _validate_emotion_continuity

        return _validate_emotion_continuity(scenes)

    def test_two_consecutive_same_emotion_warning(self, caplog):
        scenes = [
            {"speaker": "speaker_1", "context_tags": {"emotion": "happy"}},
            {"speaker": "speaker_1", "context_tags": {"emotion": "happy"}},
        ]
        with caplog.at_level(logging.WARNING):
            self._call(scenes)
        assert any("연속 중복" in r.message for r in caplog.records)
        assert any(r.levelno == logging.WARNING for r in caplog.records if "연속 중복" in r.message)

    def test_three_consecutive_same_emotion_error(self, caplog):
        scenes = [
            {"speaker": "speaker_1", "context_tags": {"emotion": "sad"}},
            {"speaker": "speaker_1", "context_tags": {"emotion": "sad"}},
            {"speaker": "speaker_1", "context_tags": {"emotion": "sad"}},
        ]
        with caplog.at_level(logging.WARNING):
            self._call(scenes)
        assert any(r.levelno == logging.ERROR for r in caplog.records if "연속 중복" in r.message)

    def test_different_emotion_resets(self, caplog):
        scenes = [
            {"speaker": "speaker_1", "context_tags": {"emotion": "happy"}},
            {"speaker": "speaker_1", "context_tags": {"emotion": "sad"}},
            {"speaker": "speaker_1", "context_tags": {"emotion": "happy"}},
        ]
        with caplog.at_level(logging.WARNING):
            self._call(scenes)
        assert not any("연속 중복" in r.message for r in caplog.records)

    def test_none_emotion_breaks_streak(self, caplog):
        scenes = [
            {"speaker": "speaker_1", "context_tags": {"emotion": "happy"}},
            {"speaker": "speaker_1", "context_tags": {"emotion": None}},
            {"speaker": "speaker_1", "context_tags": {"emotion": "happy"}},
        ]
        with caplog.at_level(logging.WARNING):
            self._call(scenes)
        assert not any("연속 중복" in r.message for r in caplog.records)

    def test_missing_context_tags_breaks_streak(self, caplog):
        scenes = [
            {"speaker": "speaker_1", "context_tags": {"emotion": "happy"}},
            {"speaker": "speaker_1"},
            {"speaker": "speaker_1", "context_tags": {"emotion": "happy"}},
        ]
        with caplog.at_level(logging.WARNING):
            self._call(scenes)
        assert not any("연속 중복" in r.message for r in caplog.records)

    def test_emotion_list_uses_first_element(self, caplog):
        """emotion이 list인 경우 첫 번째 요소만 사용."""
        scenes = [
            {"speaker": "speaker_1", "context_tags": {"emotion": ["happy", "excited"]}},
            {"speaker": "speaker_1", "context_tags": {"emotion": "happy"}},
        ]
        with caplog.at_level(logging.WARNING):
            self._call(scenes)
        assert any("연속 중복" in r.message for r in caplog.records)

    def test_single_scene_no_detection(self, caplog):
        scenes = [
            {"speaker": "speaker_1", "context_tags": {"emotion": "happy"}},
        ]
        with caplog.at_level(logging.WARNING):
            self._call(scenes)
        assert not any("연속 중복" in r.message for r in caplog.records)

    def test_different_speakers_no_detection(self, caplog):
        """다른 speaker는 연속으로 카운트하지 않음."""
        scenes = [
            {"speaker": "speaker_1", "context_tags": {"emotion": "happy"}},
            {"speaker": "speaker_2", "context_tags": {"emotion": "happy"}},
            {"speaker": "speaker_1", "context_tags": {"emotion": "happy"}},
        ]
        with caplog.at_level(logging.WARNING):
            self._call(scenes)
        assert not any("연속 중복" in r.message for r in caplog.records)

    def test_narrator_also_checked(self, caplog):
        """Narrator도 동일 로직 적용."""
        scenes = [
            {"speaker": "narrator", "context_tags": {"emotion": "calm"}},
            {"speaker": "narrator", "context_tags": {"emotion": "calm"}},
        ]
        with caplog.at_level(logging.WARNING):
            self._call(scenes)
        assert any("연속 중복" in r.message for r in caplog.records)

    def test_empty_scenes_no_crash(self, caplog):
        with caplog.at_level(logging.WARNING):
            self._call([])
        assert not any("연속 중복" in r.message for r in caplog.records)
