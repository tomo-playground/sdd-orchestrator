"""동적 max_new_tokens 계산 및 truncation guard 테스트."""

from services.video.tts_helpers import _calculate_max_new_tokens, _check_truncation


class TestCalculateMaxNewTokens:
    """텍스트 길이 기반 동적 max_new_tokens 계산."""

    def test_short_text_uses_base(self):
        """짧은 텍스트(5자)는 BASE(1024) 반환."""
        result = _calculate_max_new_tokens("안녕하세요")
        assert result == 1024  # 5 * 40 = 200 < 1024 → base

    def test_long_text_scales_up(self):
        """긴 텍스트(50자)는 동적 계산값 반환."""
        text = "가" * 50
        result = _calculate_max_new_tokens(text)
        assert result == 50 * 40  # 2000

    def test_very_long_text_capped(self):
        """매우 긴 텍스트는 CAP(3072)으로 제한."""
        text = "가" * 100
        result = _calculate_max_new_tokens(text)
        assert result == 3072  # 100 * 40 = 4000 > 3072 → cap

    def test_instruct_overhead_added(self):
        """instruct(voice_design)이 길면 overhead가 추가된다."""
        # dynamic=1040, overhead=50 → 1090 > base(1024) → overhead가 반영됨
        text = "가" * 26  # 26 * 40 = 1040
        instruct = "a" * 200  # overhead = 200 // 4 = 50
        result = _calculate_max_new_tokens(text, instruct)
        assert result == 1090  # 1040 + 50

    def test_instruct_overhead_respects_cap(self):
        """instruct overhead 포함 후에도 CAP 이하."""
        text = "가" * 76  # 76 * 40 = 3040
        instruct = "a" * 200  # overhead=50 → 3040+50=3090 > 3072
        result = _calculate_max_new_tokens(text, instruct)
        assert result == 3072  # CAP 적용

    def test_empty_instruct_same_as_no_instruct(self):
        """빈 instruct는 overhead 없음."""
        text = "가" * 50
        assert _calculate_max_new_tokens(text) == _calculate_max_new_tokens(text, "")


class TestCheckTruncation:
    """Truncation guard 헬퍼 테스트."""

    def test_short_duration_is_truncated(self):
        """텍스트 대비 duration이 너무 짧으면 truncation."""
        # 20자 * 0.065s = 1.3s 필요, 0.3s는 truncation
        assert _check_truncation(True, 0.3, "가" * 20) is True

    def test_normal_duration_not_truncated(self):
        """정상 duration은 truncation 아님."""
        assert _check_truncation(True, 2.0, "가" * 20) is False

    def test_quality_failed_skips_check(self):
        """quality_passed=False면 truncation 체크 스킵 (이미 실패)."""
        assert _check_truncation(False, 0.1, "가" * 20) is False

    def test_boundary_duration(self):
        """경계값: len*0.065와 정확히 같으면 truncation 아님."""
        text = "가" * 20  # 20 * 0.065 = 1.3s
        assert _check_truncation(True, 1.3, text) is False

    def test_short_text_min_floor(self):
        """극단적 짧은 텍스트(1자)는 최소 0.3초 보장."""
        assert _check_truncation(True, 0.2, "네") is True
        assert _check_truncation(True, 0.4, "네") is False
