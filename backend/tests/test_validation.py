"""Tests for image validation service (WD14 and Gemini comparison)."""

from services.validation import compare_prompt_to_tags


class TestComparePromptToTags:
    """Test prompt-to-tags comparison logic."""

    def test_exact_match(self):
        """Should match tags exactly."""
        prompt = "1girl, blue hair, red eyes, school uniform"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
            {"tag": "red eyes", "score": 0.88, "category": "0"},
            {"tag": "school uniform", "score": 0.85, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        assert "1girl" in result["matched"]
        assert "blue_hair" in result["matched"]
        assert "red_eyes" in result["matched"]
        assert "school_uniform" in result["matched"]
        assert len(result["missing"]) == 0

    def test_partial_match(self):
        """Should identify missing tags."""
        prompt = "1girl, blue hair, red eyes, school uniform, library"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        assert "1girl" in result["matched"]
        assert "blue_hair" in result["matched"]
        assert "red_eyes" in result["missing"]
        assert "school_uniform" in result["missing"]
        assert "library" in result["missing"]

    def test_extra_tags(self):
        """Should identify extra tags in image."""
        prompt = "1girl, blue hair"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
            {"tag": "smile", "score": 0.85, "category": "0"},
            {"tag": "outdoors", "score": 0.80, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        assert "smile" in result["extra"]
        assert "outdoors" in result["extra"]

    def test_skip_quality_tags(self):
        """Should skip quality/style tags that aren't visually detectable."""
        prompt = "masterpiece, best quality, 1girl, blue hair"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # Quality tags should be excluded from comparison
        assert "masterpiece" not in result["matched"]
        assert "masterpiece" not in result["missing"]
        assert "best_quality" not in result["missing"]

    def test_skip_lighting_tags(self):
        """Should skip lighting tags (hard to detect)."""
        prompt = "1girl, soft lighting, natural light, blue hair"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # Lighting tags should be excluded
        assert "soft_lighting" not in result["missing"]
        assert "natural_light" not in result["missing"]
        assert "1girl" in result["matched"]
        assert "blue_hair" in result["matched"]

    def test_skip_mood_tags(self):
        """Should skip abstract mood tags."""
        prompt = "1girl, peaceful, romantic, mysterious, blue hair"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # Mood tags should be excluded
        assert "peaceful" not in result["missing"]
        assert "romantic" not in result["missing"]
        assert "mysterious" not in result["missing"]

    def test_skip_time_tags(self):
        """Should skip most time-of-day tags (hard to detect)."""
        prompt = "1girl, morning, night, dawn, blue hair"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # Most time tags should be excluded
        assert "morning" not in result["missing"]
        assert "night" not in result["missing"]
        assert "dawn" not in result["missing"]

    def test_multiple_character_count_tags(self):
        """Should handle different character count tags."""
        prompt = "2girls, blue hair, red eyes"
        tags = [
            {"tag": "2girls", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
            {"tag": "red eyes", "score": 0.88, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # Should match 2girls
        assert "2girls" in result["matched"]
        assert "blue_hair" in result["matched"]
        assert "red_eyes" in result["matched"]

    def test_substring_matching(self):
        """Should match partial strings (e.g., 'hair' in 'blue hair')."""
        prompt = "1girl, hair, eyes"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
            {"tag": "red eyes", "score": 0.88, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # "hair" should match "blue_hair"
        assert "hair" in result["matched"]
        assert "eyes" in result["matched"]

    def test_empty_prompt(self):
        """Should handle empty prompt gracefully."""
        prompt = ""
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        assert result["matched"] == []
        assert result["missing"] == []
        assert result["extra"] == []

    def test_empty_tags(self):
        """Should handle empty tags list gracefully."""
        prompt = "1girl, blue hair, red eyes"
        tags = []

        result = compare_prompt_to_tags(prompt, tags)

        # All prompt tokens should be missing
        assert "1girl" in result["missing"]
        assert "blue_hair" in result["missing"]
        assert "red_eyes" in result["missing"]
        assert len(result["extra"]) == 0

    def test_case_insensitivity(self):
        """Should match tags case-insensitively."""
        prompt = "1GIRL, BLUE HAIR, Red Eyes"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
            {"tag": "red eyes", "score": 0.88, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        assert "1girl" in result["matched"]
        assert "blue_hair" in result["matched"]
        assert "red_eyes" in result["matched"]

    def test_ignore_lora_tags(self):
        """Should ignore LoRA/model tags in comparison."""
        prompt = "1girl, <lora:test:0.8>, blue hair"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # LoRA tags should be ignored
        assert "<lora:test:0.8>" not in result["matched"]
        assert "<lora:test:0.8>" not in result["missing"]
        assert "1girl" in result["matched"]
        assert "blue_hair" in result["matched"]

    def test_extra_tags_limit(self):
        """Should limit extra tags to top 20."""
        prompt = "1girl"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            *[{"tag": f"tag_{i}", "score": 0.90 - i * 0.01, "category": "0"} for i in range(30)]
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # Should only include top 20 extra tags
        assert len(result["extra"]) <= 20

    def test_complex_scenario(self):
        """Should handle complex real-world scenario."""
        prompt = "masterpiece, best quality, 1girl, blue hair, red eyes, school uniform, standing, library, soft lighting"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
            {"tag": "school uniform", "score": 0.85, "category": "0"},
            {"tag": "standing", "score": 0.80, "category": "0"},
            {"tag": "smile", "score": 0.75, "category": "0"},  # Extra
            {"tag": "indoors", "score": 0.70, "category": "0"},  # Extra
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # Matched: 1girl, blue_hair, school_uniform, standing
        assert "1girl" in result["matched"]
        assert "blue_hair" in result["matched"]
        assert "school_uniform" in result["matched"]
        assert "standing" in result["matched"]

        # Missing: red_eyes, library (quality/lighting excluded)
        assert "red_eyes" in result["missing"]
        assert "library" in result["missing"]

        # Quality/lighting tags should be excluded
        assert "masterpiece" not in result["matched"]
        assert "masterpiece" not in result["missing"]
        assert "soft_lighting" not in result["missing"]

        # Extra: smile, indoors (not in prompt)
        assert "smile" in result["extra"] or "indoors" in result["extra"]


class TestValidationIntegration:
    """Integration tests for validation workflow."""

    def test_match_rate_calculation(self):
        """Should calculate match rate correctly."""
        prompt = "1girl, blue hair, red eyes, school uniform"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
            {"tag": "school uniform", "score": 0.85, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # 3 matched out of 4 tokens = 75% match rate
        total_tokens = len(result["matched"]) + len(result["missing"])
        if total_tokens > 0:
            match_rate = len(result["matched"]) / total_tokens
            assert match_rate == 0.75

    def test_high_match_scenario(self):
        """Should achieve high match rate for good prompts."""
        prompt = "1girl, long hair, blue eyes, school uniform, standing"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "long hair", "score": 0.92, "category": "0"},
            {"tag": "blue eyes", "score": 0.90, "category": "0"},
            {"tag": "school uniform", "score": 0.88, "category": "0"},
            {"tag": "standing", "score": 0.85, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # All 5 tokens should match
        assert len(result["matched"]) == 5
        assert len(result["missing"]) == 0

    def test_low_match_scenario(self):
        """Should detect low match rate for mismatched prompts."""
        prompt = "1girl, blue hair, red eyes, school uniform, library"
        tags = [
            {"tag": "1boy", "score": 0.95, "category": "0"},
            {"tag": "blonde hair", "score": 0.90, "category": "0"},
            {"tag": "outdoors", "score": 0.85, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # Very few matches expected
        assert len(result["matched"]) < 2
        assert len(result["missing"]) >= 3
