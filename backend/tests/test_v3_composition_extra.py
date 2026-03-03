"""추가 테스트: V3PromptBuilder 미커버 함수 — resolve_aliases, clothing_override,
resolve_camera_conflicts, ensure_framing_tag, compose_background, get_effective_lora_weight,
_resolve_location_conflicts, _parse_reference_tags, select_style_trigger_words.
"""

from unittest.mock import MagicMock, patch

import pytest

from services.prompt.v3_composition import (
    LAYER_ACTION,
    LAYER_ATMOSPHERE,
    LAYER_CAMERA,
    LAYER_ENVIRONMENT,
    LAYER_IDENTITY,
    LAYER_MAIN_CLOTH,
    LAYER_QUALITY,
    LAYER_SUBJECT,
    LoRAInfo,
    V3PromptBuilder,
    select_style_trigger_words,
)


@pytest.fixture
def builder():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    return V3PromptBuilder(mock_db)


# ── select_style_trigger_words ───────────────────────────────────────


class TestSelectStyleTriggerWords:
    def test_style_multiple_returns_first(self):
        assert select_style_trigger_words(["shinkai", "kimi no na wa"], "style") == ["shinkai"]

    def test_style_single_returns_all(self):
        assert select_style_trigger_words(["flat_color"], "style") == ["flat_color"]

    def test_non_style_returns_all(self):
        result = select_style_trigger_words(["trigger_a", "trigger_b"], "character")
        assert result == ["trigger_a", "trigger_b"]

    def test_empty_list(self):
        assert select_style_trigger_words([], "style") == []


# ── _resolve_aliases ─────────────────────────────────────────────────


class TestResolveAliases:
    @patch("services.keywords.db_cache.TagAliasCache.initialize")
    @patch(
        "services.keywords.db_cache.TagAliasCache.get_replacement",
        side_effect=lambda t: "brown_hair" if t == "brunette" else None if t == "bad" else ...,
    )
    def test_replaces_and_drops(self, mock_rep, mock_init, builder):
        result = builder._resolve_aliases(["brunette", "smile", "bad"])
        assert result == ["brown_hair", "smile"]

    @patch("services.keywords.db_cache.TagAliasCache.initialize")
    @patch("services.keywords.db_cache.TagAliasCache.get_replacement", return_value=...)
    def test_no_aliases(self, mock_rep, mock_init, builder):
        result = builder._resolve_aliases(["1girl", "smile"])
        assert result == ["1girl", "smile"]


# ── _resolve_aliases_positional ──────────────────────────────────────


class TestResolveAliasesPositional:
    @patch("services.keywords.db_cache.TagAliasCache.initialize")
    @patch(
        "services.keywords.db_cache.TagAliasCache.get_replacement",
        side_effect=lambda t: None if t == "bad" else ...,
    )
    def test_dropped_becomes_none(self, mock_rep, mock_init, builder):
        result = builder._resolve_aliases_positional(["smile", "bad", "grin"])
        assert result == ["smile", None, "grin"]


# ── _resolve_location_conflicts ──────────────────────────────────────


class TestResolveLocationConflicts:
    def test_no_conflict(self, builder):
        result = builder._resolve_location_conflicts(["park", "outdoors", "bench"])
        assert "park" in result
        assert "outdoors" in result

    def test_indoor_outdoor_conflict_outdoor_wins(self, builder):
        result = builder._resolve_location_conflicts(["park", "outdoors", "classroom", "indoors"])
        # 2 outdoor vs 1 indoor → outdoor wins (park+outdoors ≥ classroom+indoors)
        assert "park" in result or "outdoors" in result
        # indoor tags should not be in result
        assert "classroom" not in result

    def test_empty_tokens(self, builder):
        assert builder._resolve_location_conflicts([]) == []


# ── _resolve_camera_conflicts ────────────────────────────────────────


class TestResolveCameraConflicts:
    def test_keeps_first_framing(self, builder):
        result = builder._resolve_camera_conflicts(["cowboy_shot", "close_up", "from_side"])
        assert "cowboy_shot" in result
        assert "close_up" not in result
        assert "from_side" in result

    def test_no_framing_all_kept(self, builder):
        result = builder._resolve_camera_conflicts(["from_side", "from_behind"])
        assert result == ["from_side", "from_behind"]

    def test_empty(self, builder):
        assert builder._resolve_camera_conflicts([]) == []

    def test_single_framing(self, builder):
        result = builder._resolve_camera_conflicts(["upper_body"])
        assert result == ["upper_body"]


# ── _ensure_framing_tag ──────────────────────────────────────────────


class TestEnsureFramingTag:
    def test_adds_full_body_for_standing(self, builder):
        layers = [[] for _ in range(12)]
        layers[LAYER_ACTION].append("standing")
        builder._ensure_framing_tag(layers)
        assert "full_body" in layers[LAYER_CAMERA]

    def test_existing_framing_no_add(self, builder):
        layers = [[] for _ in range(12)]
        layers[LAYER_CAMERA].append("cowboy_shot")
        layers[LAYER_ACTION].append("standing")
        builder._ensure_framing_tag(layers)
        assert "full_body" not in layers[LAYER_CAMERA]

    def test_no_standing_no_add(self, builder):
        layers = [[] for _ in range(12)]
        layers[LAYER_ACTION].append("sitting")
        builder._ensure_framing_tag(layers)
        assert "full_body" not in layers[LAYER_CAMERA]


# ── _apply_clothing_override ─────────────────────────────────────────


class TestApplyClothingOverride:
    def test_clears_and_distributes(self, builder):
        layers = [[] for _ in range(12)]
        layers[LAYER_MAIN_CLOTH] = ["school_uniform"]
        builder._apply_clothing_override(["casual_dress", "earrings"], layers)
        # school_uniform cleared, casual_dress added
        assert "school_uniform" not in layers[LAYER_MAIN_CLOTH]

    def test_empty_override(self, builder):
        layers = [[] for _ in range(12)]
        layers[LAYER_MAIN_CLOTH] = ["school_uniform"]
        builder._apply_clothing_override([], layers)
        assert layers[LAYER_MAIN_CLOTH] == []  # 기존도 클리어


# ── get_effective_lora_weight ────────────────────────────────────────


class TestGetEffectiveLoraWeight:
    def test_optimal_weight_priority(self, builder):
        lora = MagicMock()
        lora.optimal_weight = 0.5
        lora.default_weight = 0.8
        assert builder.get_effective_lora_weight(lora) == 0.5

    def test_default_weight_fallback(self, builder):
        lora = MagicMock()
        lora.optimal_weight = None
        lora.default_weight = 0.8
        assert builder.get_effective_lora_weight(lora) == 0.8

    def test_no_weight_returns_07(self, builder):
        lora = MagicMock()
        lora.optimal_weight = None
        lora.default_weight = None
        assert builder.get_effective_lora_weight(lora) == 0.7


# ── get_last_composed_layers ─────────────────────────────────────────


class TestGetLastComposedLayers:
    def test_none_when_not_composed(self, builder):
        assert builder.get_last_composed_layers() is None

    def test_returns_non_empty_layers(self, builder):
        builder._last_composed_layers = [["masterpiece"], [], ["1girl"], [], [], [], [], [], [], [], [], []]
        result = builder.get_last_composed_layers()
        assert len(result) == 2
        assert result[0]["tokens"] == ["masterpiece"]


# ── _parse_reference_tags ────────────────────────────────────────────


class TestParseReferenceTags:
    @patch("services.keywords.db_cache.TagFilterCache.initialize")
    @patch("services.keywords.db_cache.TagFilterCache.is_restricted", return_value=False)
    def test_parses_comma_separated(self, mock_r, mock_init, builder):
        result = builder._parse_reference_tags("1girl, smile, brown_hair")
        assert result == ["1girl", "smile", "brown_hair"]

    @patch("services.keywords.db_cache.TagFilterCache.initialize")
    @patch("services.keywords.db_cache.TagFilterCache.is_restricted", return_value=False)
    def test_empty_string(self, mock_r, mock_init, builder):
        assert builder._parse_reference_tags("") == []

    def test_none_input(self, builder):
        assert builder._parse_reference_tags(None) == []

    @patch("services.keywords.db_cache.TagFilterCache.initialize")
    @patch(
        "services.keywords.db_cache.TagFilterCache.is_restricted",
        side_effect=lambda t: t == "restricted_tag",
    )
    def test_restricted_filtered(self, mock_r, mock_init, builder):
        result = builder._parse_reference_tags("1girl, restricted_tag, smile")
        assert result == ["1girl", "smile"]


# ── _infer_layer_from_pattern (additional coverage) ──────────────────


class TestInferLayerFromPatternExtra:
    def test_lighting_suffix(self, builder):
        assert builder._infer_layer_from_pattern("dramatic_lighting") == LAYER_ATMOSPHERE

    def test_shot_suffix(self, builder):
        assert builder._infer_layer_from_pattern("wide_shot") == LAYER_CAMERA

    def test_room_suffix(self, builder):
        assert builder._infer_layer_from_pattern("living_room") == LAYER_ENVIRONMENT

    def test_background_suffix(self, builder):
        assert builder._infer_layer_from_pattern("white_background") == LAYER_ENVIRONMENT

    def test_unknown_default(self, builder):
        assert builder._infer_layer_from_pattern("totally_unknown_xyz") == LAYER_SUBJECT


# ── compose_background ──────────────────────────────────────────────


class TestComposeBackgroundScene:
    @patch("services.keywords.db_cache.TagAliasCache.initialize")
    @patch("services.keywords.db_cache.TagAliasCache.get_replacement", return_value=...)
    def test_basic_background(self, mock_rep, mock_init, builder):
        result = builder._compose_background_scene(
            scene_tags=["park", "outdoors", "no_humans", "scenery"],
        )
        assert "no_humans" in result
        assert "park" in result

    @patch("services.keywords.db_cache.TagAliasCache.initialize")
    @patch("services.keywords.db_cache.TagAliasCache.get_replacement", return_value=...)
    def test_background_with_style_loras(self, mock_rep, mock_init, builder):
        result = builder._compose_background_scene(
            scene_tags=["forest", "no_humans"],
            style_loras=[{"name": "flat_color", "weight": 0.4}],
        )
        assert "<lora:flat_color:" in result
        assert "forest" in result
