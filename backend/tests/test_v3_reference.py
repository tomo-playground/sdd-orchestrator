"""Tests for V3PromptBuilder.compose_for_reference() — reference image prompt composition."""

from unittest.mock import MagicMock, patch

import pytest

from services.prompt.v3_composition import (
    LAYER_CAMERA,
    LAYER_ENVIRONMENT,
    LAYER_QUALITY,
    V3PromptBuilder,
)


@pytest.fixture
def builder():
    """Create V3PromptBuilder with mocked DB session."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.first.return_value = None
    return V3PromptBuilder(mock_db)


def _make_character(
    gender=None,
    loras=None,
    reference_base_prompt=None,
    custom_base_prompt=None,
    prompt_mode="auto",
):
    """Helper to build a mock Character."""
    char = MagicMock()
    char.gender = gender
    char.loras = loras or []
    char.reference_base_prompt = reference_base_prompt
    char.custom_base_prompt = custom_base_prompt
    char.prompt_mode = prompt_mode
    char.tags = []
    return char


# ────────────────────────────────────────────
# Quality tags
# ────────────────────────────────────────────


class TestReferenceQualityTags:
    """compose_for_reference must include masterpiece + best_quality."""

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagFilterCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
    def test_quality_tags_present(self, mock_alias, mock_filter, mock_rule, builder):
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        char = _make_character()
        result = builder.compose_for_reference(char)

        assert "masterpiece" in result
        assert "best_quality" in result


# ────────────────────────────────────────────
# Environment tags (white_background fixed)
# ────────────────────────────────────────────


class TestReferenceEnvironmentTags:
    """Reference images must have white_background + simple_background."""

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagFilterCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
    def test_environment_defaults_injected(self, mock_alias, mock_filter, mock_rule, builder):
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        char = _make_character()
        result = builder.compose_for_reference(char)

        assert "white_background" in result
        assert "simple_background" in result

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagFilterCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
    def test_camera_defaults_injected(self, mock_alias, mock_filter, mock_rule, builder):
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        char = _make_character()
        result = builder.compose_for_reference(char)

        assert "solo" in result
        assert "looking_at_viewer" in result


# ────────────────────────────────────────────
# Character LoRA weight scaling
# ────────────────────────────────────────────


class TestReferenceCharacterLoRA:
    """Character LoRAs should be scaled by REFERENCE_LORA_SCALE (0.4)."""

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagFilterCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
    def test_character_lora_weight_scaled(self, mock_alias, mock_filter, mock_rule, builder):
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        # Mock LoRA DB lookup
        lora_obj = MagicMock()
        lora_obj.id = 1
        lora_obj.name = "midoriya_lora"
        lora_obj.lora_type = "character"
        lora_obj.trigger_words = ["Midoriya_Izuku"]
        lora_obj.optimal_weight = None
        lora_obj.default_weight = None
        builder.db.query.return_value.filter.return_value.all.return_value = [lora_obj]

        char = _make_character(loras=[{"lora_id": 1, "weight": 0.8}])
        result = builder.compose_for_reference(char)

        # 0.8 * 0.4 = 0.32 (REFERENCE_LORA_SCALE=0.4)
        assert "<lora:midoriya_lora:0.32>" in result
        # Trigger word should be included
        assert "Midoriya_Izuku" in result


# ────────────────────────────────────────────
# Style LoRA full weight
# ────────────────────────────────────────────


class TestReferenceStyleLoRA:
    """Style LoRAs should keep full weight (not skipped like in scene compose)."""

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagFilterCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
    def test_style_lora_full_weight(self, mock_alias, mock_filter, mock_rule, builder):
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        # Mock LoRA DB lookup
        lora_obj = MagicMock()
        lora_obj.id = 2
        lora_obj.name = "flat_color"
        lora_obj.lora_type = "style"
        lora_obj.trigger_words = []
        lora_obj.optimal_weight = 0.65
        lora_obj.default_weight = None
        builder.db.query.return_value.filter.return_value.all.return_value = [lora_obj]

        char = _make_character(loras=[{"lora_id": 2, "weight": 0.7}])
        result = builder.compose_for_reference(char)

        # Style LoRA: 0.7 × REFERENCE_STYLE_LORA_SCALE(0.3) = 0.21
        assert "<lora:flat_color:0.21>" in result

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagFilterCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
    def test_style_lora_capped(self, mock_alias, mock_filter, mock_rule, builder):
        """Style LoRA weight 0.9 → capped to 0.76."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        lora_obj = MagicMock()
        lora_obj.id = 2
        lora_obj.name = "flat_color"
        lora_obj.lora_type = "style"
        lora_obj.trigger_words = []
        lora_obj.optimal_weight = None
        lora_obj.default_weight = None
        builder.db.query.return_value.filter.return_value.all.return_value = [lora_obj]

        char = _make_character(loras=[{"lora_id": 2, "weight": 0.9}])
        result = builder.compose_for_reference(char)

        # Style LoRA: 0.9 × REFERENCE_STYLE_LORA_SCALE(0.3) = 0.27 (below cap)
        assert "<lora:flat_color:0.27>" in result
        assert "<lora:flat_color:0.9>" not in result


# ────────────────────────────────────────────
# Tag deduplication
# ────────────────────────────────────────────


class TestReferenceDedup:
    """Tags should not appear duplicated in the final prompt."""

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagFilterCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
    def test_no_duplicate_tags(self, mock_alias, mock_filter, mock_rule, builder):
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        # Character with tag that also appears in reference_base_prompt
        char_tag = MagicMock()
        char_tag.tag = MagicMock()
        char_tag.tag.name = "solo"
        char_tag.tag.default_layer = LAYER_CAMERA
        char_tag.weight = 1.0

        char = _make_character(reference_base_prompt="solo, white_background")
        char.tags = [char_tag]

        result = builder.compose_for_reference(char)

        # "solo" should appear only once
        tokens = [t.strip() for t in result.split(",")]
        solo_count = sum(1 for t in tokens if t == "solo")
        assert solo_count == 1, f"Expected 1 'solo', got {solo_count} in: {result}"


# ────────────────────────────────────────────
# Male gender enhancement
# ────────────────────────────────────────────


class TestReferenceGenderEnhancement:
    """Male characters should get gender enhancement in reference prompts."""

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagFilterCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
    def test_male_enhancement(self, mock_alias, mock_filter, mock_rule, builder):
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        char = _make_character(gender="male")
        result = builder.compose_for_reference(char)

        assert "(1boy:1.3)" in result
        assert "(male_focus:1.2)" in result

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagFilterCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
    def test_female_no_enhancement(self, mock_alias, mock_filter, mock_rule, builder):
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        char = _make_character(gender="female")
        result = builder.compose_for_reference(char)

        assert "(1boy:1.3)" not in result
        assert "(male_focus:1.2)" not in result


# ────────────────────────────────────────────
# _parse_reference_tags
# ────────────────────────────────────────────


class TestParseReferenceTags:
    """Test _parse_reference_tags helper."""

    @patch("services.prompt.v3_composition.TagFilterCache")
    def test_parses_comma_separated(self, mock_filter, builder):
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False

        result = builder._parse_reference_tags("solo, white_background, front_view")
        assert result == ["solo", "white_background", "front_view"]

    @patch("services.prompt.v3_composition.TagFilterCache")
    def test_filters_restricted(self, mock_filter, builder):
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.side_effect = lambda t: t == "restricted_tag"

        result = builder._parse_reference_tags("solo, restricted_tag, front_view")
        assert "restricted_tag" not in result
        assert "solo" in result

    @patch("services.prompt.v3_composition.TagFilterCache")
    def test_empty_prompt(self, mock_filter, builder):
        mock_filter.initialize.return_value = None
        assert builder._parse_reference_tags(None) == []
        assert builder._parse_reference_tags("") == []


# ────────────────────────────────────────────
# _inject_reference_defaults
# ────────────────────────────────────────────


class TestInjectReferenceDefaults:
    """Test _inject_reference_defaults helper."""

    def test_injects_env_and_camera(self, builder):
        layers = [[] for _ in range(12)]
        builder._inject_reference_defaults(layers)

        # Env tags are injected into LAYER_QUALITY for maximum SD priority
        quality = layers[LAYER_QUALITY]
        assert "(white_background:1.8)" in quality
        assert "(simple_background:1.5)" in quality
        assert "plain_background" in quality
        assert "solid_background" in quality
        assert "(solo:1.5)" in layers[LAYER_CAMERA]
        assert "looking_at_viewer" in layers[LAYER_CAMERA]
        assert "front_view" in layers[LAYER_CAMERA]
        assert "straight_on" in layers[LAYER_CAMERA]

    def test_no_duplicate_if_already_present(self, builder):
        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["(white_background:1.8)"]
        layers[LAYER_CAMERA] = ["(solo:1.5)"]

        builder._inject_reference_defaults(layers)

        assert layers[LAYER_QUALITY].count("(white_background:1.8)") == 1
        assert layers[LAYER_CAMERA].count("(solo:1.5)") == 1
