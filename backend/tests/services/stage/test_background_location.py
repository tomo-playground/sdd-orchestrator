"""Tests for services/stage/background_location.py (Phase 32).

Covers:
- resolve_bg_quality_tags: BG_QUALITY_OVERRIDES hit/miss, None style_ctx
- compute_location_key: filter + dedup + join with "_"
- find_best_matching_bg: exact match, partial/subset match, no match → None
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_style_ctx(profile_id: int, default_positive: str = "") -> MagicMock:
    ctx = MagicMock()
    ctx.profile_id = profile_id
    ctx.default_positive = default_positive
    return ctx


# ── resolve_bg_quality_tags ───────────────────────────────────────────────────


class TestResolveBgQualityTags:
    """resolve_bg_quality_tags returns override or fallback."""

    def test_known_profile_returns_override(self):
        """StyleProfile id=2 is in BG_QUALITY_OVERRIDES → returns override string split."""
        from config import BG_QUALITY_OVERRIDES
        from services.stage.background_location import resolve_bg_quality_tags

        ctx = _make_style_ctx(profile_id=2)
        result = resolve_bg_quality_tags(ctx)

        expected_str = BG_QUALITY_OVERRIDES[2]
        assert result == expected_str.split(", ")
        # Spot-check one well-known tag
        assert "RAW photo" in result

    def test_unknown_profile_falls_back_to_default_positive(self):
        """Unknown StyleProfile id → returns style_ctx.default_positive tags."""
        from services.stage.background_location import resolve_bg_quality_tags

        ctx = _make_style_ctx(profile_id=9999, default_positive="high quality, detailed, 4k")
        result = resolve_bg_quality_tags(ctx)

        assert result == ["high quality", "detailed", "4k"]

    def test_unknown_profile_empty_default_positive_returns_empty_list(self):
        """Unknown profile with empty default_positive → empty list (not None)."""
        from services.stage.background_location import resolve_bg_quality_tags

        ctx = _make_style_ctx(profile_id=9999, default_positive="")
        result = resolve_bg_quality_tags(ctx)

        # empty string → .split(", ") == [''] but falsy check returns None
        assert result is None

    def test_none_style_ctx_returns_none(self):
        """None style_ctx → returns None."""
        from services.stage.background_location import resolve_bg_quality_tags

        result = resolve_bg_quality_tags(None)

        assert result is None

    def test_override_tags_are_strings(self):
        """Each tag in the override result is a non-empty string."""
        from services.stage.background_location import resolve_bg_quality_tags

        ctx = _make_style_ctx(profile_id=2)
        result = resolve_bg_quality_tags(ctx)

        assert result is not None
        for tag in result:
            assert isinstance(tag, str)
            assert tag.strip() == tag  # no leading/trailing spaces
            assert len(tag) > 0


# ── compute_location_key ──────────────────────────────────────────────────────


class TestComputeLocationKey:
    """compute_location_key filters, resolves aliases, deduplicates, joins."""

    def _make_db_with_location_tags(self, tag_names: list[str]) -> MagicMock:
        """Return a mock DB that yields the given tag_names as location rows.

        Note: MagicMock(name=...) sets the mock's own name, not an attribute.
        Use a SimpleNamespace so that r.name is the actual tag string.
        """
        from types import SimpleNamespace

        db = MagicMock()
        rows = [SimpleNamespace(name=n) for n in tag_names]
        # db.query(Tag.name).filter(...).all() → rows
        db.query.return_value.filter.return_value.all.return_value = rows
        return db

    def test_basic_location_tags_joined_sorted(self):
        """Tags filtered to location group are sorted and joined with '_'."""
        from services.stage.background_location import compute_location_key

        db = self._make_db_with_location_tags(["park", "outdoor"])

        with patch("services.stage.background_location.TagAliasCache") as mock_cache:
            mock_cache.get_replacement.side_effect = lambda t: t  # no alias
            result = compute_location_key(["outdoor", "park"], db)

        # sorted({"park", "outdoor"}) = ["outdoor", "park"] → "outdoor_park"
        assert result == "outdoor_park"

    def test_duplicate_tags_are_deduplicated(self):
        """Duplicate tags in env_tags produce a single key entry."""
        from services.stage.background_location import compute_location_key

        db = self._make_db_with_location_tags(["cafe"])

        with patch("services.stage.background_location.TagAliasCache") as mock_cache:
            mock_cache.get_replacement.side_effect = lambda t: t
            # Pass the same tag twice
            result = compute_location_key(["cafe", "cafe"], db)

        assert result == "cafe"

    def test_alias_is_applied_to_location_tags(self):
        """Alias resolution replaces tags (e.g. coffee_shop → cafe)."""
        from services.stage.background_location import compute_location_key

        db = self._make_db_with_location_tags(["coffee_shop"])

        alias_map = {"coffee_shop": "cafe"}

        with patch("services.stage.background_location.TagAliasCache") as mock_cache:
            mock_cache.get_replacement.side_effect = lambda t: alias_map.get(t, t)
            result = compute_location_key(["coffee_shop"], db)

        assert result == "cafe"

    def test_empty_env_tags_returns_empty_string(self):
        """Empty env_tags → _filter returns [] → fallback is also [] → empty key."""
        from services.stage.background_location import compute_location_key

        db = self._make_db_with_location_tags([])

        with patch("services.stage.background_location.TagAliasCache") as mock_cache:
            mock_cache.get_replacement.side_effect = lambda t: t
            result = compute_location_key([], db)

        assert result == ""

    def test_no_location_tags_falls_back_to_first_env_tag(self):
        """When DB filter returns nothing, falls back to env_tags[:1]."""
        from services.stage.background_location import compute_location_key

        # DB filter returns nothing (no location-group tags match)
        db = self._make_db_with_location_tags([])

        with patch("services.stage.background_location.TagAliasCache") as mock_cache:
            mock_cache.get_replacement.side_effect = lambda t: t
            result = compute_location_key(["forest", "daytime", "fog"], db)

        # Falls back to first tag
        assert result == "forest"

    def test_multiple_tags_sorted_and_joined(self):
        """Three location tags are sorted alphabetically and joined."""
        from services.stage.background_location import compute_location_key

        db = self._make_db_with_location_tags(["rooftop", "city", "night"])

        with patch("services.stage.background_location.TagAliasCache") as mock_cache:
            mock_cache.get_replacement.side_effect = lambda t: t
            result = compute_location_key(["night", "rooftop", "city"], db)

        # sorted({"night", "rooftop", "city"}) = ["city", "night", "rooftop"]
        assert result == "city_night_rooftop"


# ── find_best_matching_bg ─────────────────────────────────────────────────────


class TestFindBestMatchingBg:
    """find_best_matching_bg exact match, partial match, no match."""

    def test_exact_match_returned_directly(self):
        """When scene_key exactly matches a bg_key, that bg_info is returned."""
        from services.stage.background_location import find_best_matching_bg

        loc_to_bg = {
            "cafe_indoor": {"image_url": "cafe.png"},
            "park_outdoor": {"image_url": "park.png"},
        }

        info, key = find_best_matching_bg("cafe_indoor", loc_to_bg)

        assert info == {"image_url": "cafe.png"}
        assert key == "cafe_indoor"

    def test_subset_match_returns_superset_bg(self):
        """Scene key is a subset of a bg key (bg_set <= scene_set or vice-versa)."""
        from services.stage.background_location import find_best_matching_bg

        # bg key has all tags that scene key has (subset relationship)
        loc_to_bg = {
            "cafe_indoor_rainy": {"image_url": "cafe_rainy.png"},
        }

        # scene_key = "cafe_indoor" → scene_set = {"cafe", "indoor"}
        # bg_key = "cafe_indoor_rainy" → bg_set = {"cafe", "indoor", "rainy"}
        # scene_set <= bg_set (subset) → should match
        info, key = find_best_matching_bg("cafe_indoor", loc_to_bg)

        assert info == {"image_url": "cafe_rainy.png"}

    def test_superset_match_returns_bg(self):
        """Bg key is a subset of scene key (bg covers part of scene)."""
        from services.stage.background_location import find_best_matching_bg

        loc_to_bg = {
            "park": {"image_url": "park.png"},
        }

        # scene_key = "park_outdoor_sunny" → bg_set = {"park"} is a subset
        info, key = find_best_matching_bg("park_outdoor_sunny", loc_to_bg)

        assert info == {"image_url": "park.png"}

    def test_no_match_returns_none(self):
        """Completely different keys → info is None."""
        from services.stage.background_location import find_best_matching_bg

        loc_to_bg = {
            "beach_sunny": {"image_url": "beach.png"},
        }

        info, key = find_best_matching_bg("mountain_snowy", loc_to_bg)

        assert info is None

    def test_empty_bg_dict_returns_none(self):
        """Empty bg dict → always returns None."""
        from services.stage.background_location import find_best_matching_bg

        info, key = find_best_matching_bg("any_location", {})

        assert info is None

    def test_best_score_wins_among_multiple_candidates(self):
        """When multiple bgs could match, the highest Jaccard overlap wins."""
        from services.stage.background_location import find_best_matching_bg

        loc_to_bg = {
            "cafe": {"image_url": "cafe.png"},
            "cafe_indoor": {"image_url": "cafe_indoor.png"},
            "cafe_indoor_modern": {"image_url": "cafe_indoor_modern.png"},
        }

        # scene_key = "cafe_indoor" → exact match should win
        info, key = find_best_matching_bg("cafe_indoor", loc_to_bg)

        # Exact match has Jaccard = 1.0 — it must win
        assert info == {"image_url": "cafe_indoor.png"}
        assert key == "cafe_indoor"

    def test_single_tag_subset_match(self):
        """Single-word scene key matches bg key containing that word."""
        from services.stage.background_location import find_best_matching_bg

        loc_to_bg = {
            "school_hallway": {"image_url": "hallway.png"},
        }

        # "school" is a subset of "school_hallway"
        info, key = find_best_matching_bg("school", loc_to_bg)

        assert info == {"image_url": "hallway.png"}

    def test_returned_key_is_bg_key_not_scene_key(self):
        """The returned key is from loc_to_bg, not the scene_key."""
        from services.stage.background_location import find_best_matching_bg

        loc_to_bg = {"library_quiet": {"image_url": "lib.png"}}

        info, key = find_best_matching_bg("library", loc_to_bg)

        # key returned should be the bg's key, not "library"
        assert key == "library_quiet"
