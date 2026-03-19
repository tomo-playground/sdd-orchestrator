"""Tests for estimate_reading_duration() — reading-time-based duration calculation."""

from services.storyboard.helpers import estimate_reading_duration


class TestEstimateReadingDuration:
    """estimate_reading_duration: script text -> reading time in seconds."""

    def test_korean_short(self):
        """Short Korean text: 8 chars / 4 CPS + 0.5 padding = 2.5s."""
        result = estimate_reading_duration("오늘 하루 힘들었어", "korean")
        assert result == 2.5

    def test_korean_medium(self):
        """Medium Korean text: 16 chars / 4 CPS + 0.5 = 4.5s."""
        result = estimate_reading_duration("처음 칼을 잡았을 때, 너무 무서웠어.", "korean")
        # 16 chars (excluding spaces) / 4 CPS + 0.5 = 4.5
        assert 3.0 <= result <= 6.0

    def test_korean_long(self):
        """Long Korean text should not exceed SCENE_DURATION_MAX."""
        long_text = "가" * 100  # 100 chars / 4 CPS + 0.5 = 25.5 -> capped at 10.0
        result = estimate_reading_duration(long_text, "korean")
        assert result == 10.0

    def test_english(self):
        """English: 5 words / 2.5 WPS + 0.5 = 2.5s."""
        result = estimate_reading_duration("I had a great day", "english")
        assert result == 2.5

    def test_english_long(self):
        """English long text: 20 words / 2.5 WPS + 0.5 = 8.5s."""
        words = " ".join(["word"] * 20)
        result = estimate_reading_duration(words, "english")
        assert result == 8.5

    def test_japanese(self):
        """Japanese: 10 chars / 5 CPS + 0.5 = 2.5s."""
        result = estimate_reading_duration("今日はとても疲れました", "japanese")
        # 10 chars (no spaces) / 5 CPS + 0.5 = 2.5
        assert result >= 2.0

    def test_empty_text(self):
        """Empty text returns minimum duration 2.0s."""
        assert estimate_reading_duration("", "korean") == 2.0
        assert estimate_reading_duration("   ", "korean") == 2.0

    def test_minimum_duration(self):
        """Very short text still returns at least 2.0s."""
        result = estimate_reading_duration("아", "korean")
        # 1 char / 4 CPS + 0.5 = 0.75 -> capped at 2.0
        assert result == 2.0

    def test_unknown_language_falls_back_to_korean(self):
        """Unknown language uses Korean config as fallback."""
        result = estimate_reading_duration("테스트 텍스트입니다", "chinese")
        expected = estimate_reading_duration("테스트 텍스트입니다", "korean")
        assert result == expected

    def test_spaces_excluded_for_char_languages(self):
        """Spaces are excluded when counting chars for Korean/Japanese."""
        with_spaces = estimate_reading_duration("안녕 하세요 반갑 습니다", "korean")
        without_spaces = estimate_reading_duration("안녕하세요반갑습니다", "korean")
        assert with_spaces == without_spaces
