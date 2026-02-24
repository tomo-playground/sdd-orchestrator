"""Tests for identity score calculation (Phase 16-C)."""

from __future__ import annotations

from services.identity_score import compute_identity_score, extract_character_identity_tags


class TestExtractCharacterIdentityTags:
    """Test extraction of identity-relevant tags from character tag list."""

    def test_extracts_identity_groups(self):
        tags = [
            {"name": "black_hair", "group_name": "hair_color"},
            {"name": "blue_eyes", "group_name": "eye_color"},
            {"name": "long_hair", "group_name": "hair_length"},
            {"name": "school_uniform", "group_name": "clothing"},
            {"name": "smile", "group_name": "expression"},
        ]
        result = extract_character_identity_tags(tags)
        assert "black_hair" in result
        assert "blue_eyes" in result
        assert "long_hair" in result
        assert "school_uniform" not in result  # clothing excluded
        assert "smile" not in result  # expression excluded

    def test_empty_tags(self):
        assert extract_character_identity_tags([]) == []

    def test_no_identity_groups(self):
        tags = [
            {"name": "smile", "group_name": "expression"},
            {"name": "standing", "group_name": "pose"},
            {"name": "cowboy_shot", "group_name": "camera"},
        ]
        assert extract_character_identity_tags(tags) == []

    def test_normalizes_tokens(self):
        tags = [{"name": "Black Hair", "group_name": "hair_color"}]
        result = extract_character_identity_tags(tags)
        assert "black_hair" in result


class TestComputeIdentityScore:
    """Test identity score computation."""

    def test_perfect_match(self):
        identity_tags = ["black_hair", "blue_eyes"]
        wd14_tags = [
            {"tag": "black_hair", "score": 0.90},
            {"tag": "blue_eyes", "score": 0.85},
            {"tag": "smile", "score": 0.70},
        ]
        assert compute_identity_score(identity_tags, wd14_tags) == 1.0

    def test_partial_match(self):
        identity_tags = ["black_hair", "blue_eyes", "long_hair"]
        wd14_tags = [
            {"tag": "black_hair", "score": 0.90},
            {"tag": "smile", "score": 0.70},
        ]
        score = compute_identity_score(identity_tags, wd14_tags)
        assert abs(score - 1 / 3) < 0.001

    def test_no_match(self):
        identity_tags = ["black_hair", "blue_eyes"]
        wd14_tags = [
            {"tag": "blonde_hair", "score": 0.90},
            {"tag": "red_eyes", "score": 0.85},
        ]
        assert compute_identity_score(identity_tags, wd14_tags) == 0.0

    def test_empty_identity_tags_returns_one(self):
        """No identity constraints → perfect score."""
        wd14_tags = [{"tag": "black_hair", "score": 0.90}]
        assert compute_identity_score([], wd14_tags) == 1.0

    def test_threshold_filtering(self):
        identity_tags = ["black_hair", "blue_eyes"]
        wd14_tags = [
            {"tag": "black_hair", "score": 0.90},
            {"tag": "blue_eyes", "score": 0.20},  # Below threshold
        ]
        score = compute_identity_score(identity_tags, wd14_tags, threshold=0.35)
        assert abs(score - 0.5) < 0.001

    def test_empty_wd14_tags(self):
        identity_tags = ["black_hair"]
        assert compute_identity_score(identity_tags, []) == 0.0

    def test_normalized_matching(self):
        """WD14 tags with spaces should match normalized identity tags."""
        identity_tags = ["black_hair"]
        wd14_tags = [{"tag": "black hair", "score": 0.90}]
        assert compute_identity_score(identity_tags, wd14_tags) == 1.0

    def test_multiple_identity_features(self):
        identity_tags = ["black_hair", "blue_eyes", "long_hair", "ponytail", "glasses"]
        wd14_tags = [
            {"tag": "black_hair", "score": 0.90},
            {"tag": "blue_eyes", "score": 0.85},
            {"tag": "long_hair", "score": 0.80},
        ]
        score = compute_identity_score(identity_tags, wd14_tags)
        assert abs(score - 3 / 5) < 0.001
