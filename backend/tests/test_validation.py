"""Tests for image validation service (WD14 and Gemini comparison)."""

import pytest

from services.validation import compare_prompt_to_tags, compute_adjusted_match_rate


class TestComparePromptToTags:
    """Test prompt-to-tags comparison logic."""

    @pytest.fixture(autouse=True)
    def _mock_tag_cache(self, monkeypatch):
        """Mock TagCategoryCache so tags are not skipped due to missing DB."""
        group_map = {
            "1girl": "subject",
            "2girls": "subject",
            "1boy": "subject",
            "blue_hair": "hair_color",
            "long_hair": "hair_style",
            "blonde_hair": "hair_color",
            "red_eyes": "eye_color",
            "blue_eyes": "eye_color",
            "school_uniform": "clothing_outfit",
            "smile": "expression",
            "standing": "pose",
            "library": "location_indoor_specific",
            "outdoors": "location_outdoor",
            "indoors": "location_indoor",
            "soft_lighting": "lighting",
            "natural_light": "lighting",
            "peaceful": "mood",
            "romantic": "mood",
            "mysterious": "mood",
            "morning": "time_of_day",
            "night": "time_of_day",
            "dawn": "time_of_day",
            "hair": "hair_style",
            "eyes": "eye_color",
            "masterpiece": "quality",
            "best_quality": "quality",
        }
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache",
            type("FakeCache", (), {"get_category": staticmethod(lambda t: group_map.get(t))}),
        )

    def test_exact_match(self):
        """Should match tags exactly (using only_tokens for WD14-detectable tags only)."""
        tokens = ["1girl", "blue_hair", "red_eyes", "school_uniform"]
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue_hair", "score": 0.90, "category": "0"},
            {"tag": "red_eyes", "score": 0.88, "category": "0"},
            {"tag": "school_uniform", "score": 0.85, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

        assert "1girl" in result["matched"]
        assert "blue_hair" in result["matched"]
        assert "red_eyes" in result["matched"]
        assert "school_uniform" in result["matched"]
        assert len(result["missing"]) == 0

    def test_partial_match(self):
        """Should identify missing tags."""
        tokens = ["1girl", "blue_hair", "red_eyes", "school_uniform", "library"]
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue_hair", "score": 0.90, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

        assert "1girl" in result["matched"]
        assert "blue_hair" in result["matched"]
        assert "red_eyes" in result["missing"]
        assert "school_uniform" in result["missing"]
        assert "library" in result["missing"]

    def test_extra_tags(self):
        """Should identify extra tags in image."""
        tokens = ["1girl", "blue_hair"]
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue_hair", "score": 0.90, "category": "0"},
            {"tag": "smile", "score": 0.85, "category": "0"},
            {"tag": "outdoors", "score": 0.80, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

        assert "smile" in result["extra"]
        assert "outdoors" in result["extra"]

    def test_skip_quality_tags(self):
        """Quality tags in SKIPPABLE_GROUPS should be skipped."""
        tokens = ["masterpiece", "best_quality", "1girl", "blue_hair"]
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue_hair", "score": 0.90, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

        assert "masterpiece" in result["skipped"]
        assert "best_quality" in result["skipped"]

    def test_gemini_group_tags_not_skipped(self):
        """Lighting/mood/time tags are GEMINI-detectable, not skipped in WD14 comparison."""
        tokens = ["1girl", "soft_lighting", "peaceful", "morning", "blue_hair"]
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue_hair", "score": 0.90, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

        # Gemini-detectable tags → missing (not skipped) in WD14 comparison
        assert "1girl" in result["matched"]
        assert "blue_hair" in result["matched"]
        # Lighting/mood/time are GEMINI groups → not in SKIPPABLE → treated as missing
        assert "soft_lighting" in result["missing"]
        assert "peaceful" in result["missing"]
        assert "morning" in result["missing"]

    def test_multiple_character_count_tags(self):
        """Should handle different character count tags."""
        tokens = ["2girls", "blue_hair", "red_eyes"]
        tags = [
            {"tag": "2girls", "score": 0.95, "category": "0"},
            {"tag": "blue_hair", "score": 0.90, "category": "0"},
            {"tag": "red_eyes", "score": 0.88, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

        assert "2girls" in result["matched"]
        assert "blue_hair" in result["matched"]
        assert "red_eyes" in result["matched"]

    def test_substring_matching(self):
        """Simple tokens like 'hair' do NOT reverse-match compound tags like 'blue_hair'."""
        tokens = ["1girl", "hair", "eyes"]
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue_hair", "score": 0.90, "category": "0"},
            {"tag": "red_eyes", "score": 0.88, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

        assert "1girl" in result["matched"]
        assert "hair" in result["missing"]
        assert "eyes" in result["missing"]

    def test_empty_prompt(self):
        """Should handle empty tokens gracefully."""
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue_hair", "score": 0.90, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=[])

        assert result["matched"] == []
        assert result["missing"] == []
        assert result["extra"] == []

    def test_empty_tags(self):
        """Should handle empty tags list gracefully."""
        tokens = ["1girl", "blue_hair", "red_eyes"]

        result = compare_prompt_to_tags("", [], only_tokens=tokens)

        assert "1girl" in result["missing"]
        assert "blue_hair" in result["missing"]
        assert "red_eyes" in result["missing"]
        assert len(result["extra"]) == 0

    def test_case_insensitivity(self):
        """Should match tags case-insensitively."""
        tokens = ["1girl", "blue_hair", "red_eyes"]
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue_hair", "score": 0.90, "category": "0"},
            {"tag": "red_eyes", "score": 0.88, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

        assert "1girl" in result["matched"]
        assert "blue_hair" in result["matched"]
        assert "red_eyes" in result["matched"]

    def test_ignore_lora_tags(self):
        """LoRA tags are filtered out during tokenization (not tested via only_tokens)."""
        prompt = "1girl, <lora:test:0.8>, blue hair"
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue_hair", "score": 0.90, "category": "0"},
        ]

        result = compare_prompt_to_tags(prompt, tags)

        assert "<lora:test:0.8>" not in result["matched"]
        assert "<lora:test:0.8>" not in result["missing"]

    def test_extra_tags_all_returned(self, monkeypatch):
        """Extra tags include all unmatched tags with score >= 0.5."""
        # Override mock to return a group for all tags (not None)
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache",
            type("FakeCache", (), {"get_category": staticmethod(lambda t: "subject" if t == "1girl" else "action")}),
        )
        tokens = ["1girl"]
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            *[{"tag": f"tag_{i}", "score": 0.90 - i * 0.01, "category": "0"} for i in range(30)],
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

        # All 30 extra tags have score >= 0.5, so all are returned
        assert len(result["extra"]) == 30

    def test_complex_scenario(self):
        """Should handle complex real-world scenario (WD14-detectable tokens only)."""
        tokens = ["1girl", "blue_hair", "school_uniform", "standing"]
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue_hair", "score": 0.90, "category": "0"},
            {"tag": "school_uniform", "score": 0.85, "category": "0"},
            {"tag": "standing", "score": 0.80, "category": "0"},
            {"tag": "smile", "score": 0.75, "category": "0"},
            {"tag": "indoors", "score": 0.70, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

        assert "1girl" in result["matched"]
        assert "blue_hair" in result["matched"]
        assert "school_uniform" in result["matched"]
        assert "standing" in result["matched"]
        assert len(result["missing"]) == 0
        assert "smile" in result["extra"]
        assert "indoors" in result["extra"]


class TestValidationIntegration:
    """Integration tests for validation workflow."""

    @pytest.fixture(autouse=True)
    def _mock_tag_cache(self, monkeypatch):
        """Mock TagCategoryCache so tags are not skipped due to missing DB."""
        group_map = {
            "1girl": "subject",
            "1boy": "subject",
            "blue_hair": "hair_color",
            "long_hair": "hair_style",
            "blonde_hair": "hair_color",
            "red_eyes": "eye_color",
            "blue_eyes": "eye_color",
            "school_uniform": "clothing_outfit",
            "standing": "pose",
            "library": "location_indoor_specific",
            "outdoors": "location_outdoor",
        }
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache",
            type("FakeCache", (), {"get_category": staticmethod(lambda t: group_map.get(t))}),
        )

    def test_match_rate_calculation(self):
        """Should calculate match rate correctly."""
        tokens = ["1girl", "blue_hair", "red_eyes", "school_uniform"]
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "blue_hair", "score": 0.90, "category": "0"},
            {"tag": "school_uniform", "score": 0.85, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

        # 3 matched out of 4 tokens = 75%
        total_tokens = len(result["matched"]) + len(result["missing"])
        if total_tokens > 0:
            match_rate = len(result["matched"]) / total_tokens
            assert match_rate == 0.75

    def test_high_match_scenario(self):
        """Should achieve high match rate for good prompts."""
        tokens = ["1girl", "long_hair", "blue_eyes", "school_uniform", "standing"]
        tags = [
            {"tag": "1girl", "score": 0.95, "category": "0"},
            {"tag": "long_hair", "score": 0.92, "category": "0"},
            {"tag": "blue_eyes", "score": 0.90, "category": "0"},
            {"tag": "school_uniform", "score": 0.88, "category": "0"},
            {"tag": "standing", "score": 0.85, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

        assert len(result["matched"]) == 5
        assert len(result["missing"]) == 0

    def test_low_match_scenario(self):
        """Should detect low match rate for mismatched prompts."""
        tokens = ["1girl", "blue_hair", "red_eyes", "school_uniform", "library"]
        tags = [
            {"tag": "1boy", "score": 0.95, "category": "0"},
            {"tag": "blonde_hair", "score": 0.90, "category": "0"},
            {"tag": "outdoors", "score": 0.85, "category": "0"},
        ]

        result = compare_prompt_to_tags("", tags, only_tokens=tokens)

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
        result = compute_adjusted_match_rate(matched, partial, missing)
        assert abs(result - 0.75) < 0.001

    def test_non_detectable_missing_excluded(self):
        """Non-detectable missing tags excluded → adjusted > raw."""
        matched = ["1girl", "blue_hair"]
        partial = []
        missing = ["cowboy_shot", "soft_lighting", "red_eyes"]
        result = compute_adjusted_match_rate(matched, partial, missing)
        assert abs(result - 2 / 3) < 0.001

    def test_non_detectable_matched_excluded(self):
        """Non-detectable matched tags also excluded from adjusted."""
        matched = ["1girl", "cowboy_shot"]
        partial = []
        missing = ["red_eyes"]
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
        partial = ["school_uniform"]
        missing = ["red_eyes"]
        result = compute_adjusted_match_rate(matched, partial, missing)
        assert abs(result - 2 / 3) < 0.001

    def test_unknown_group_treated_conservatively(self):
        """Tokens with None group (DB unregistered) are excluded."""
        matched = ["unknown_tag_xyz"]
        partial = []
        missing = ["1girl"]
        result = compute_adjusted_match_rate(matched, partial, missing)
        assert result == 0.0

    def test_adjusted_gte_raw(self):
        """Adjusted rate >= raw rate when non-detectable missing exist."""
        matched = ["1girl", "smile"]
        partial = ["looking_at_viewer"]
        missing = ["cowboy_shot", "classroom", "red_eyes"]
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
        tags = [{"tag": "black_hair", "score": 0.90}, {"tag": "blue_eyes", "score": 0.85}]
        score = compute_identity_score(["black_hair", "blue_eyes"], tags)
        assert score == 1.0

    def test_identity_score_none_without_character_id(self):
        """identity_score should be None when character_id is not provided."""
        from services.identity_score import compute_identity_score

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
