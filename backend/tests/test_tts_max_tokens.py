"""동적 max_new_tokens 계산 테스트.

_calculate_max_new_tokens()가 텍스트 길이에 따라
적절한 토큰 수를 반환하는지 검증한다.
"""

from services.video.tts_helpers import _calculate_max_new_tokens


class TestCalculateMaxNewTokens:
    """텍스트 길이 기반 동적 max_new_tokens 계산."""

    def test_short_text_uses_base(self):
        """짧은 텍스트(10자)는 BASE(1024) 반환."""
        result = _calculate_max_new_tokens("안녕하세요")
        assert result == 1024  # 5 * 30 = 150 < 1024 → base

    def test_long_text_scales_up(self):
        """긴 텍스트(50자)는 동적 계산값 반환."""
        text = "가" * 50
        result = _calculate_max_new_tokens(text)
        assert result == 50 * 30  # 1500

    def test_very_long_text_capped(self):
        """매우 긴 텍스트는 CAP(2048)으로 제한."""
        text = "가" * 100
        result = _calculate_max_new_tokens(text)
        assert result == 2048  # 100 * 30 = 3000 > 2048 → cap

    def test_instruct_overhead_added(self):
        """instruct(voice_design)이 길면 overhead가 추가된다."""
        # dynamic=990, overhead=50 → 1040 > base(1024) → overhead가 반영됨
        text = "가" * 33  # 33 * 30 = 990
        instruct = "a" * 200  # overhead = 200 // 4 = 50
        result = _calculate_max_new_tokens(text, instruct)
        assert result == 1040  # 990 + 50

    def test_instruct_overhead_respects_cap(self):
        """instruct overhead 포함 후에도 CAP 이하."""
        text = "가" * 68  # 68 * 30 = 2040
        instruct = "a" * 200  # overhead=50 → 2040+50=2090 > 2048
        result = _calculate_max_new_tokens(text, instruct)
        assert result == 2048  # CAP 적용

    def test_empty_instruct_same_as_no_instruct(self):
        """빈 instruct는 overhead 없음."""
        text = "가" * 50
        assert _calculate_max_new_tokens(text) == _calculate_max_new_tokens(text, "")
