"""Test: Review 대사 품질 검증 (A-2, A-3, B-1, B-2).

validate_dialogue_quality() 순수 함수 단위 테스트.
"""

from __future__ import annotations

import re

import pytest


# ---------------------------------------------------------------------------
# A-3 helper: _jaccard_similarity
# ---------------------------------------------------------------------------
class TestJaccardSimilarity:
    """_jaccard_similarity 단위 테스트."""

    def test_identical_text(self):
        from services.agent.nodes._review_validators import _jaccard_similarity

        assert _jaccard_similarity("오늘 날씨가 좋다", "오늘 날씨가 좋다") == 1.0

    def test_completely_different(self):
        from services.agent.nodes._review_validators import _jaccard_similarity

        sim = _jaccard_similarity("오늘 날씨가 좋다", "내일 비가 온다")
        assert sim < 0.3

    def test_empty_strings(self):
        from services.agent.nodes._review_validators import _jaccard_similarity

        assert _jaccard_similarity("", "") == 0.0

    def test_one_empty(self):
        from services.agent.nodes._review_validators import _jaccard_similarity

        assert _jaccard_similarity("오늘 날씨가 좋다", "") == 0.0

    def test_boundary_similarity(self):
        """70% 이상이면 WARNING 대상 — 경계값 확인."""
        from services.agent.nodes._review_validators import _jaccard_similarity

        # 7/10 overlap → 0.7
        tokens_a = "a b c d e f g h i j"
        tokens_b = "a b c d e f g x y z"
        sim = _jaccard_similarity(tokens_a, tokens_b)
        assert sim == pytest.approx(7 / 13)  # |A∩B|=7, |A∪B|=13


# ---------------------------------------------------------------------------
# B-2 helper: _detect_speech_level
# ---------------------------------------------------------------------------
class TestDetectSpeechLevel:
    """_detect_speech_level 단위 테스트."""

    def test_formal(self):
        from services.agent.nodes._review_validators import _detect_speech_level

        assert _detect_speech_level("감사합니다 좋아요") == "formal"

    def test_informal(self):
        from services.agent.nodes._review_validators import _detect_speech_level

        assert _detect_speech_level("밥 먹어 좋지 가냐") == "informal"

    def test_empty_string(self):
        from services.agent.nodes._review_validators import _detect_speech_level

        assert _detect_speech_level("") is None

    def test_none_string(self):
        from services.agent.nodes._review_validators import _detect_speech_level

        assert _detect_speech_level(None) is None

    def test_no_indicators(self):
        from services.agent.nodes._review_validators import _detect_speech_level

        assert _detect_speech_level("구름 바람 하늘") is None

    def test_tie_returns_none(self):
        from services.agent.nodes._review_validators import _detect_speech_level

        # 반말 1개("먹어") + 존댓말 1개("좋아요") → 동률 → None
        result = _detect_speech_level("먹어 좋아요")
        assert result is None


# ---------------------------------------------------------------------------
# A-2: Speaker 교번 단절
# ---------------------------------------------------------------------------
class TestSpeakerAlternation:
    """A-2: 동일 speaker 3씬 이상 연속이면 WARNING."""

    def _call(self, scenes, structure="dialogue"):
        from services.agent.nodes._review_validators import validate_dialogue_quality

        return validate_dialogue_quality(scenes, structure)

    def test_three_consecutive_same_speaker(self):
        scenes = [
            {"script": "대사1", "speaker": "speaker_1"},
            {"script": "대사2", "speaker": "speaker_1"},
            {"script": "대사3", "speaker": "speaker_1"},
        ]
        errors, warnings = self._call(scenes)
        assert any("연속 독백" in w for w in warnings)

    def test_two_consecutive_no_warning(self):
        scenes = [
            {"script": "대사1", "speaker": "speaker_1"},
            {"script": "대사2", "speaker": "speaker_1"},
            {"script": "대사3", "speaker": "speaker_2"},
        ]
        errors, warnings = self._call(scenes)
        assert not any("연속 독백" in w for w in warnings)

    def test_monologue_skipped(self):
        scenes = [
            {"script": "대사1", "speaker": "speaker_1"},
            {"script": "대사2", "speaker": "speaker_1"},
            {"script": "대사3", "speaker": "speaker_1"},
        ]
        errors, warnings = self._call(scenes, structure="monologue")
        assert not any("연속 독백" in w for w in warnings)

    def test_narrated_dialogue_skipped(self):
        scenes = [
            {"script": "대사1", "speaker": "narrator"},
            {"script": "대사2", "speaker": "narrator"},
            {"script": "대사3", "speaker": "narrator"},
        ]
        errors, warnings = self._call(scenes, structure="narrated_dialogue")
        assert not any("연속 독백" in w for w in warnings)

    def test_narrator_breaks_streak(self):
        scenes = [
            {"script": "대사1", "speaker": "speaker_1"},
            {"script": "대사2", "speaker": "speaker_1"},
            {"script": "대사3", "speaker": "narrator"},
            {"script": "대사4", "speaker": "speaker_1"},
        ]
        errors, warnings = self._call(scenes)
        assert not any("연속 독백" in w for w in warnings)


# ---------------------------------------------------------------------------
# A-3: 인접 씬 스크립트 유사도
# ---------------------------------------------------------------------------
class TestScriptSimilarity:
    """A-3: 인접 씬 Jaccard >= 0.7이면 WARNING."""

    def _call(self, scenes, structure="dialogue"):
        from services.agent.nodes._review_validators import validate_dialogue_quality

        return validate_dialogue_quality(scenes, structure)

    def test_identical_scripts_warning(self):
        scenes = [
            {"script": "오늘 날씨가 참 좋다 정말 좋다", "speaker": "speaker_1"},
            {"script": "오늘 날씨가 참 좋다 정말 좋다", "speaker": "speaker_2"},
        ]
        errors, warnings = self._call(scenes)
        assert any("유사도" in w for w in warnings)

    def test_different_scripts_no_warning(self):
        scenes = [
            {"script": "오늘 날씨가 좋다", "speaker": "speaker_1"},
            {"script": "내일 비가 올 것이다", "speaker": "speaker_2"},
        ]
        errors, warnings = self._call(scenes)
        assert not any("유사도" in w for w in warnings)

    def test_empty_script_skipped(self):
        scenes = [
            {"script": "", "speaker": "speaker_1"},
            {"script": "오늘 날씨가 좋다", "speaker": "speaker_2"},
        ]
        errors, warnings = self._call(scenes)
        assert not any("유사도" in w for w in warnings)

    def test_none_script_skipped(self):
        scenes = [
            {"script": None, "speaker": "speaker_1"},
            {"script": "오늘 날씨가 좋다", "speaker": "speaker_2"},
        ]
        errors, warnings = self._call(scenes)
        assert not any("유사도" in w for w in warnings)


# ---------------------------------------------------------------------------
# B-1: 클리셰 감지
# ---------------------------------------------------------------------------
class TestClicheDetection:
    """B-1: 한 씬에 클리셰 2개 이상이면 WARNING."""

    def _call(self, scenes, structure="dialogue"):
        from services.agent.nodes._review_validators import validate_dialogue_quality

        return validate_dialogue_quality(scenes, structure)

    def test_two_cliches_warning(self):
        scenes = [
            {"script": "심쿵이야 이건 레전드다", "speaker": "speaker_1"},
        ]
        errors, warnings = self._call(scenes)
        assert any("클리셰" in w for w in warnings)

    def test_one_cliche_no_warning(self):
        scenes = [
            {"script": "이건 심쿵이야 진짜 감동적이다", "speaker": "speaker_1"},
        ]
        errors, warnings = self._call(scenes)
        assert not any("클리셰" in w for w in warnings)

    def test_zero_cliches_no_warning(self):
        scenes = [
            {"script": "조용히 숲을 걸었다", "speaker": "speaker_1"},
        ]
        errors, warnings = self._call(scenes)
        assert not any("클리셰" in w for w in warnings)

    def test_empty_script_skipped(self):
        scenes = [
            {"script": "", "speaker": "speaker_1"},
        ]
        errors, warnings = self._call(scenes)
        assert not any("클리셰" in w for w in warnings)


# ---------------------------------------------------------------------------
# B-1: config.py 패턴 유효성
# ---------------------------------------------------------------------------
class TestClichePatternsValid:
    """config.py의 DIALOGUE_CLICHE_PATTERNS가 유효한 정규식인지 확인."""

    def test_all_patterns_compile(self):
        from config import DIALOGUE_CLICHE_PATTERNS

        for pattern in DIALOGUE_CLICHE_PATTERNS:
            re.compile(pattern)  # 컴파일 에러 시 테스트 실패


# ---------------------------------------------------------------------------
# B-2: 문체 일관성
# ---------------------------------------------------------------------------
class TestSpeechConsistency:
    """B-2: 동일 speaker의 반말/존댓말 혼용 (각 3씬 이상) WARNING."""

    def _call(self, scenes, structure="dialogue"):
        from services.agent.nodes._review_validators import validate_dialogue_quality

        return validate_dialogue_quality(scenes, structure)

    def test_mixed_speech_warning(self):
        scenes = [
            {"script": "밥 먹어", "speaker": "speaker_1"},
            {"script": "같이 가지", "speaker": "speaker_1"},
            {"script": "그거 맞냐", "speaker": "speaker_1"},
            {"script": "좋아요", "speaker": "speaker_1"},
            {"script": "가세요", "speaker": "speaker_1"},
            {"script": "맞습니다", "speaker": "speaker_1"},
        ]
        errors, warnings = self._call(scenes)
        assert any("문체 통일" in w or "혼용" in w for w in warnings)

    def test_consistent_speech_no_warning(self):
        scenes = [
            {"script": "밥 먹어", "speaker": "speaker_1"},
            {"script": "같이 가지", "speaker": "speaker_1"},
            {"script": "재밌냐", "speaker": "speaker_1"},
            {"script": "진짜 좋게", "speaker": "speaker_1"},
        ]
        errors, warnings = self._call(scenes)
        assert not any("문체 통일" in w or "혼용" in w for w in warnings)

    def test_insufficient_scenes_no_warning(self):
        """formal 2 + informal 2 → 각각 3개 미달 → WARNING 없음."""
        scenes = [
            {"script": "밥 먹어", "speaker": "speaker_1"},
            {"script": "같이 가지", "speaker": "speaker_1"},
            {"script": "감사합니다", "speaker": "speaker_1"},
            {"script": "좋아요", "speaker": "speaker_1"},
        ]
        errors, warnings = self._call(scenes)
        assert not any("문체 통일" in w or "혼용" in w for w in warnings)

    def test_monologue_skipped(self):
        scenes = [
            {"script": "밥 먹어", "speaker": "speaker_1"},
            {"script": "같이 가지", "speaker": "speaker_1"},
            {"script": "그거 맞냐", "speaker": "speaker_1"},
            {"script": "감사합니다", "speaker": "speaker_1"},
            {"script": "좋아요", "speaker": "speaker_1"},
            {"script": "가세요", "speaker": "speaker_1"},
        ]
        errors, warnings = self._call(scenes, structure="monologue")
        assert not any("문체 통일" in w or "혼용" in w for w in warnings)


# ---------------------------------------------------------------------------
# 통합: validate_scenes()에 dialogue 검증이 포함되는지
# ---------------------------------------------------------------------------
class TestValidateScenesIntegration:
    """validate_scenes() 호출 시 dialogue 검증 warnings가 포함되는지."""

    def test_dialogue_warnings_in_validate_scenes(self):
        from services.agent.nodes._review_validators import validate_scenes

        scenes = [
            {"script": "대사1 텍스트입니다", "speaker": "speaker_1", "duration": 3, "image_prompt": "img"},
            {"script": "대사2 텍스트입니다", "speaker": "speaker_1", "duration": 3, "image_prompt": "img"},
            {"script": "대사3 텍스트입니다", "speaker": "speaker_1", "duration": 3, "image_prompt": "img"},
            {"script": "대사4 텍스트입니다", "speaker": "speaker_2", "duration": 3, "image_prompt": "img"},
            {"script": "대사5 텍스트입니다", "speaker": "speaker_2", "duration": 3, "image_prompt": "img"},
        ]
        result = validate_scenes(scenes, duration=15, language="korean", structure="dialogue")
        assert any("연속 독백" in w for w in result["warnings"])

    def test_empty_scenes_no_crash(self):
        from services.agent.nodes._review_validators import validate_scenes

        result = validate_scenes([], duration=15, language="korean", structure="dialogue")
        # scenes 부족 에러는 발생하지만 dialogue 검증에서 크래시 없음
        assert not result["passed"]
