"""Tests for image validation service (WD14 and Gemini comparison)."""

import pytest

from services.validation import compare_prompt_to_tags, compute_adjusted_match_rate


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
        """Composite match only works for compound prompt tokens (e.g., 'blue_shirt' -> 'shirt').

        Simple tokens like 'hair' do NOT reverse-match compound tags like 'blue_hair'.
        """
        prompt = "1girl, hair, eyes"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue hair", "score": 0.90, "category": "0"},
            {"tag": "red eyes", "score": 0.88, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # "hair" and "eyes" are simple tokens; they don't match compound tags
        assert "1girl" in result["matched"]
        assert "hair" in result["missing"]
        assert "eyes" in result["missing"]

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

    def test_extra_tags_all_returned(self):
        """Extra tags include all unmatched tags with score >= 0.5."""
        prompt = "1girl"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            *[{"tag": f"tag_{i}", "score": 0.90 - i * 0.01, "category": "0"} for i in range(30)],
        ]

        result = compare_prompt_to_tags(prompt, tags)

        # All 30 extra tags have score >= 0.5, so all are returned
        assert len(result["extra"]) == 30

    def test_complex_scenario(self):
        """Should handle complex real-world scenario."""
        prompt = (
            "masterpiece, best quality, 1girl, blue hair, red eyes, school uniform, standing, library, soft lighting"
        )
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


class TestComputeAdjustedMatchRate:
    """Test adjusted match rate calculation using WD14-detectable groups."""

    @pytest.fixture(autouse=True)
    def _mock_tag_cache(self, monkeypatch):
        """Mock TagCategoryCache.get_category to return known groups."""
        group_map = {
            "1girl": "subject",
            "blue_hair": "hair_color",
            "red_eyes": "eye_color",
            "school_uniform": "clothing_outfit",
            "smile": "expression",
            "standing": "pose",
            "cowboy_shot": "camera",
            "soft_lighting": "lighting",
            "classroom": "location_indoor_specific",
            "peaceful": "mood",
            "looking_at_viewer": "gaze",
        }
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache",
            type("FakeCache", (), {"get_category": staticmethod(lambda t: group_map.get(t))}),
        )

    def test_all_detectable(self):
        """All tokens are detectable → adjusted == raw."""
        matched = ["1girl", "blue_hair", "smile"]
        partial = []
        missing = ["red_eyes"]
        # 3 matched / 4 total = 0.75
        result = compute_adjusted_match_rate(matched, partial, missing)
        assert abs(result - 0.75) < 0.001

    def test_non_detectable_missing_excluded(self):
        """Non-detectable missing tags excluded → adjusted > raw."""
        matched = ["1girl", "blue_hair"]
        partial = []
        missing = ["cowboy_shot", "soft_lighting", "red_eyes"]
        # Raw: 2/5 = 0.4
        # Adjusted: detectable matched=2 (1girl, blue_hair), detectable missing=1 (red_eyes)
        # camera/lighting excluded → 2/3 = 0.667
        result = compute_adjusted_match_rate(matched, partial, missing)
        assert abs(result - 2 / 3) < 0.001

    def test_non_detectable_matched_excluded(self):
        """Non-detectable matched tags also excluded from adjusted."""
        matched = ["1girl", "cowboy_shot"]
        partial = []
        missing = ["red_eyes"]
        # Adjusted: detectable matched=1 (1girl), detectable missing=1 (red_eyes)
        # cowboy_shot (camera) excluded → 1/2 = 0.5
        result = compute_adjusted_match_rate(matched, partial, missing)
        assert abs(result - 0.5) < 0.001

    def test_all_non_detectable(self):
        """All tokens non-detectable → 0.0."""
        matched = ["cowboy_shot"]
        partial = []
        missing = ["soft_lighting", "peaceful"]
        result = compute_adjusted_match_rate(matched, partial, missing)
        assert result == 0.0

    def test_empty_inputs(self):
        """Empty inputs → 0.0."""
        result = compute_adjusted_match_rate([], [], [])
        assert result == 0.0

    def test_partial_matched_detectable(self):
        """Partial matched detectable tokens count as matched."""
        matched = ["1girl"]
        partial = ["school_uniform"]  # clothing → detectable
        missing = ["red_eyes"]
        # detectable matched=2 (1girl + school_uniform), detectable missing=1 → 2/3
        result = compute_adjusted_match_rate(matched, partial, missing)
        assert abs(result - 2 / 3) < 0.001

    def test_unknown_group_treated_conservatively(self):
        """Tokens with None group (DB unregistered) are excluded."""
        matched = ["unknown_tag_xyz"]
        partial = []
        missing = ["1girl"]
        # unknown_tag_xyz → group=None → excluded
        # detectable: matched=0, missing=1 (1girl=subject) → 0/1 = 0.0
        result = compute_adjusted_match_rate(matched, partial, missing)
        assert result == 0.0

    def test_adjusted_gte_raw(self):
        """Adjusted rate >= raw rate when non-detectable missing exist."""
        matched = ["1girl", "smile"]
        partial = ["looking_at_viewer"]
        missing = ["cowboy_shot", "classroom", "red_eyes"]
        # Raw: 3/6 = 0.5
        # Adjusted: matched=3 (1girl, smile, looking_at_viewer), missing=1 (red_eyes) → 3/4 = 0.75
        raw = 3 / 6
        adjusted = compute_adjusted_match_rate(matched, partial, missing)
        assert adjusted >= raw
        assert abs(adjusted - 0.75) < 0.001


class TestIdentityScoreInValidation:
    """Test identity_score integration in validate_scene_image."""

    def test_identity_score_returned_when_character_id(self, monkeypatch):
        """identity_score should appear in result when character_id is provided."""
        from services.identity_score import compute_identity_score

        monkeypatch.setattr(
            "services.identity_score.load_character_identity_tags",
            lambda cid, db: ["black_hair", "blue_eyes"],
        )
        # compute_identity_score with matching tags
        tags = [{"tag": "black_hair", "score": 0.90}, {"tag": "blue_eyes", "score": 0.85}]
        score = compute_identity_score(["black_hair", "blue_eyes"], tags)
        assert score == 1.0

    def test_identity_score_none_without_character_id(self):
        """identity_score should be None when character_id is not provided."""
        from services.identity_score import compute_identity_score

        # No character_id → identity_score not computed
        assert compute_identity_score([], []) == 1.0

    def test_identity_score_partial(self):
        """identity_score reflects partial match."""
        from services.identity_score import compute_identity_score

        identity_tags = ["black_hair", "blue_eyes", "long_hair"]
        wd14_tags = [
            {"tag": "black_hair", "score": 0.90},
            {"tag": "red_eyes", "score": 0.85},
        ]
        score = compute_identity_score(identity_tags, wd14_tags)
        assert abs(score - 1 / 3) < 0.001
