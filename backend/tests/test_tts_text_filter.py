"""TTS 텍스트 선별 필터 테스트.

_strip_non_speech()와 clean_script_for_tts()의 지문/메타 제거를 검증한다.
"""

from services.script.scene_postprocess import annotate_speakable
from services.video.utils import _strip_non_speech, clean_script_for_tts, has_speakable_content


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

    def test_ellipsis_with_text_preserved(self):
        """텍스트가 포함된 말줄임은 유지."""
        result = clean_script_for_tts("그래서...")
        assert "그래서" in result


class TestHasSpeakableContent:
    """has_speakable_content: TTS 생성 전 선별 함수."""

    def test_ellipsis_not_speakable(self):
        assert has_speakable_content("...") is False

    def test_dots_not_speakable(self):
        assert has_speakable_content("....") is False

    def test_single_dot_not_speakable(self):
        assert has_speakable_content(".") is False

    def test_punctuation_only_not_speakable(self):
        assert has_speakable_content("?!...") is False

    def test_empty_not_speakable(self):
        assert has_speakable_content("") is False

    def test_whitespace_not_speakable(self):
        assert has_speakable_content("   ") is False

    def test_stage_direction_only_not_speakable(self):
        """지문만 있으면 음성화 불가."""
        assert has_speakable_content("(한숨) [BGM 시작]") is False

    def test_korean_text_speakable(self):
        assert has_speakable_content("안녕하세요") is True

    def test_english_text_speakable(self):
        assert has_speakable_content("Hello world") is True

    def test_text_with_ellipsis_speakable(self):
        assert has_speakable_content("그래서...") is True

    def test_interjection_speakable(self):
        assert has_speakable_content("아... 그랬구나") is True

    def test_number_speakable(self):
        assert has_speakable_content("3만원") is True

    def test_single_char_exclamation_not_speakable(self):
        """1글자 감탄사(네?)는 TTS 최소 duration 미달 → 스킵."""
        assert has_speakable_content("네?...........") is False

    def test_single_korean_char_not_speakable(self):
        """'아...' 같은 1글자 감탄사도 스킵."""
        assert has_speakable_content("아...") is False

    def test_two_char_korean_speakable(self):
        """2글자 이상이면 TTS 진행."""
        assert has_speakable_content("네네") is True

    def test_huh_with_dots_not_speakable(self):
        """'헉...' 1글자 감탄사 스킵."""
        assert has_speakable_content("헉...") is False

    def test_short_word_speakable(self):
        """'왜요' 2글자는 TTS 진행."""
        assert has_speakable_content("왜요?") is True


class TestAnnotateSpeakable:
    """annotate_speakable: Writer 후처리에서 씬별 speakable 플래그 부여."""

    def test_normal_scenes_speakable(self):
        scenes = [
            {"script": "안녕하세요", "order": 0},
            {"script": "오늘 날씨 좋다", "order": 1},
        ]
        annotate_speakable(scenes)
        assert scenes[0]["speakable"] is True
        assert scenes[1]["speakable"] is True

    def test_ellipsis_not_speakable(self):
        scenes = [{"script": "...", "order": 0}]
        annotate_speakable(scenes)
        assert scenes[0]["speakable"] is False

    def test_mixed_scenes(self):
        scenes = [
            {"script": "처음 칼을 잡았을 때", "order": 0},
            {"script": "...", "order": 1},
            {"script": "너무 무서웠어", "order": 2},
        ]
        annotate_speakable(scenes)
        assert scenes[0]["speakable"] is True
        assert scenes[1]["speakable"] is False
        assert scenes[2]["speakable"] is True

    def test_empty_script_not_speakable(self):
        scenes = [{"script": "", "order": 0}]
        annotate_speakable(scenes)
        assert scenes[0]["speakable"] is False

    def test_stage_direction_only_not_speakable(self):
        scenes = [{"script": "(한숨) [BGM 시작]", "order": 0}]
        annotate_speakable(scenes)
        assert scenes[0]["speakable"] is False

    def test_preserves_existing_fields(self):
        scenes = [{"script": "안녕", "order": 0, "speaker": "A", "duration": 3}]
        annotate_speakable(scenes)
        assert scenes[0]["speakable"] is True
        assert scenes[0]["speaker"] == "A"
        assert scenes[0]["duration"] == 3
