"""Tests for prompt_builders — language tempo rules + critic quality rules (SP-107)."""

from services.agent.prompt_builders_c import build_korean_quality_rules
from services.agent.prompt_builders_writer import build_korean_rules_block


class TestBuildKoreanRulesBlock:
    """build_korean_rules_block() 한국어 반환값 검증."""

    def test_korean_returns_tempo_rules(self):
        result = build_korean_rules_block("korean")
        assert "쇼츠 템포 규칙" in result

    def test_korean_contains_scene_split_rule(self):
        result = build_korean_rules_block("korean")
        assert "한 문장 = 한 정보" in result

    def test_korean_contains_hook_prohibition(self):
        result = build_korean_rules_block("korean")
        assert "인사/예고 절대 금지" in result

    def test_korean_contains_cta_rule(self):
        result = build_korean_rules_block("korean")
        assert "10자 이하" in result
        assert "명령형" in result

    def test_korean_contains_interjection_rule(self):
        result = build_korean_rules_block("korean")
        assert "감탄사" in result
        assert "삽입 권장" in result

    def test_korean_14char_limit(self):
        """기존 15자 → 14자로 변경 확인."""
        result = build_korean_rules_block("korean")
        assert "14자 권장" in result
        assert "15자 권장" not in result

    def test_korean_rule_numbering(self):
        """규칙 12번으로 추가됨을 확인."""
        result = build_korean_rules_block("korean")
        assert "12." in result


class TestJapaneseTempoRules:
    """build_korean_rules_block("japanese") 일본어 템포 규칙 검증."""

    def test_japanese_returns_tempo_block(self):
        result = build_korean_rules_block("japanese")
        assert result != ""
        assert "テンポ" in result

    def test_japanese_scene_split_rule(self):
        result = build_korean_rules_block("japanese")
        assert "1シーン = 1文 = 1情報" in result

    def test_japanese_hook_prohibition(self):
        result = build_korean_rules_block("japanese")
        assert "挨拶/予告" in result

    def test_japanese_cta_rule(self):
        result = build_korean_rules_block("japanese")
        assert "12文字以下" in result
        assert "命令形" in result

    def test_japanese_interjection_examples(self):
        result = build_korean_rules_block("japanese")
        assert "マジで。" in result


class TestEnglishTempoRules:
    """build_korean_rules_block("english") 영어 템포 규칙 검증."""

    def test_english_returns_tempo_block(self):
        result = build_korean_rules_block("english")
        assert result != ""
        assert "Tempo Rules" in result

    def test_english_scene_split_rule(self):
        result = build_korean_rules_block("english")
        assert "one sentence = one idea" in result

    def test_english_hook_prohibition(self):
        result = build_korean_rules_block("english")
        assert "No greetings" in result

    def test_english_cta_rule(self):
        result = build_korean_rules_block("english")
        assert "5 words max" in result

    def test_english_interjection_examples(self):
        result = build_korean_rules_block("english")
        assert "No way." in result


class TestUnsupportedLanguage:
    """미지원 언어는 빈 문자열 반환."""

    def test_unknown_language_returns_empty(self):
        assert build_korean_rules_block("chinese") == ""

    def test_empty_language_returns_empty(self):
        assert build_korean_rules_block("") == ""


class TestBuildKoreanQualityRules:
    """build_korean_quality_rules() — Critic 14자 초과 경고 규칙 검증 (SP-107 P2)."""

    def test_korean_contains_14char_warning(self):
        result = build_korean_quality_rules("korean")
        assert "14자 초과" in result

    def test_korean_contains_one_scene_one_info(self):
        result = build_korean_quality_rules("korean")
        assert "한 문장 = 한 정보" in result

    def test_non_korean_returns_empty(self):
        assert build_korean_quality_rules("english") == ""
        assert build_korean_quality_rules("japanese") == ""
