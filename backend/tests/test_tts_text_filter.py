"""TTS 텍스트 선별 필터 테스트.

_strip_non_speech()와 clean_script_for_tts()의 지문/메타 제거를 검증한다.
"""

from services.video.utils import _strip_non_speech, clean_script_for_tts


class TestStripNonSpeech:
    """_strip_non_speech: 지문/메타/해시태그 제거."""

    def test_parenthetical_stage_direction(self):
        assert _strip_non_speech("(한숨) 힘들다...") == "힘들다..."

    def test_multiple_parenthetical(self):
        assert _strip_non_speech("(조용히) 괜찮아. (미소)") == "괜찮아."

    def test_bracket_meta(self):
        assert _strip_non_speech("[BGM 시작] 안녕하세요") == "안녕하세요"

    def test_bracket_visual_cue(self):
        assert _strip_non_speech("[카메라 줌인] 이게 뭐야?") == "이게 뭐야?"

    def test_hashtags(self):
        assert _strip_non_speech("오늘 #일상 #직장인") == "오늘"

    def test_asterisk_sfx(self):
        assert _strip_non_speech("*문 닫히는 소리* 누구야?") == "누구야?"

    def test_interjection_preserved(self):
        """감탄사는 괄호 없으면 유지."""
        assert _strip_non_speech("아... 그랬구나") == "아... 그랬구나"

    def test_sigh_without_parens(self):
        """괄호 없는 감탄사 유지."""
        assert _strip_non_speech("하... 진짜 힘들다") == "하... 진짜 힘들다"

    def test_pure_speech_unchanged(self):
        assert _strip_non_speech("오늘 날씨 좋다!") == "오늘 날씨 좋다!"

    def test_complex_mixed(self):
        result = _strip_non_speech("(놀라며) [효과음] 진짜?! #반전 *두둥*")
        assert result == "진짜?!"

    def test_empty_after_strip(self):
        """지문만 있으면 빈 문자열."""
        assert _strip_non_speech("(한숨) [BGM]") == ""

    def test_whitespace_collapse(self):
        assert _strip_non_speech("(웃음)  정말  그래?") == "정말 그래?"


class TestCleanScriptForTtsWithFilter:
    """clean_script_for_tts: 지문 제거 + 기존 정규화 통합."""

    def test_stage_direction_removed(self):
        result = clean_script_for_tts("(한숨) 오늘도 야근이야...")
        assert "한숨" not in result
        assert "오늘도 야근이야" in result

    def test_bracket_removed_with_normalization(self):
        result = clean_script_for_tts("[나레이션] 3만원짜리 커피를 마셨다")
        assert "나레이션" not in result
        assert "삼만원" in result

    def test_hashtag_removed(self):
        result = clean_script_for_tts("맛있다! #먹방 #일상")
        assert "#" not in result
        assert "맛있다!" in result

    def test_interjection_survives_full_pipeline(self):
        result = clean_script_for_tts("아... 그랬구나")
        assert "아" in result
        assert "그랬구나" in result

    def test_all_non_speech_returns_empty(self):
        result = clean_script_for_tts("(한숨) [BGM 시작] #태그")
        assert result == ""
