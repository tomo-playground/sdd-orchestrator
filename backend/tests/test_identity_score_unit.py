"""identity_score 순수 함수 단위 테스트."""

from __future__ import annotations

from services.identity_score import (
    compute_identity_score,
    extract_character_identity_tags,
)


# ── extract_character_identity_tags ───────────────────────


class TestExtractCharacterIdentityTags:
    def test_extracts_identity_groups_only(self):
        tags = [
            {"name": "black_hair", "group_name": "hair_color"},
            {"name": "blue_eyes", "group_name": "eye_color"},
            {"name": "smile", "group_name": "expression"},
            {"name": "school_uniform", "group_name": "clothing"},
        ]
        result = extract_character_identity_tags(tags)
        assert "black_hair" in result
        assert "blue_eyes" in result
        # expression and clothing are not identity groups
        assert "smile" not in result
        assert "school_uniform" not in result

    def test_empty_input(self):
        assert extract_character_identity_tags([]) == []

    def test_no_identity_groups(self):
        tags = [
            {"name": "smile", "group_name": "expression"},
            {"name": "standing", "group_name": "pose"},
        ]
        assert extract_character_identity_tags(tags) == []

    def test_missing_group_name(self):
        tags = [{"name": "test_tag", "group_name": ""}]
        assert extract_character_identity_tags(tags) == []

    def test_normalizes_tag_names(self):
        tags = [{"name": "black hair", "group_name": "hair_color"}]
        result = extract_character_identity_tags(tags)
        assert len(result) == 1
        assert result[0] == "black_hair"


# ── compute_identity_score ────────────────────────────────


class TestComputeIdentityScore:
    def test_perfect_match(self):
        identity = ["black_hair", "blue_eyes"]
        wd14 = [
            {"tag": "black_hair", "score": 0.9},
            {"tag": "blue_eyes", "score": 0.8},
        ]
        assert compute_identity_score(identity, wd14) == 1.0

    def test_partial_match(self):
        identity = ["black_hair", "blue_eyes"]
        wd14 = [
            {"tag": "black_hair", "score": 0.9},
            {"tag": "green_eyes", "score": 0.8},
        ]
        assert compute_identity_score(identity, wd14) == 0.5

    def test_no_match(self):
        identity = ["black_hair", "blue_eyes"]
        wd14 = [{"tag": "brown_hair", "score": 0.9}]
        assert compute_identity_score(identity, wd14) == 0.0

    def test_empty_identity_returns_one(self):
        assert compute_identity_score([], [{"tag": "brown_hair", "score": 0.9}]) == 1.0

    def test_threshold_filtering(self):
        identity = ["black_hair"]
        wd14 = [{"tag": "black_hair", "score": 0.2}]
        # Default threshold is 0.35, so 0.2 should not match
        assert compute_identity_score(identity, wd14) == 0.0

    def test_custom_threshold(self):
        identity = ["black_hair"]
        wd14 = [{"tag": "black_hair", "score": 0.2}]
        assert compute_identity_score(identity, wd14, threshold=0.1) == 1.0
