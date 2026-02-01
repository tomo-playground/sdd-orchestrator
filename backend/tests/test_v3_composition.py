"""Tests for V3PromptBuilder: _flatten_layers, _dedup_key, gender enhancement."""

from unittest.mock import MagicMock

import pytest

from services.prompt.v3_composition import (
    LAYER_ACTION,
    LAYER_ENVIRONMENT,
    LAYER_EXPRESSION,
    LAYER_IDENTITY,
    LAYER_QUALITY,
    LAYER_SUBJECT,
    V3PromptBuilder,
)


@pytest.fixture
def builder():
    """Create V3PromptBuilder with mocked DB session."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    return V3PromptBuilder(mock_db)


# ────────────────────────────────────────────
# _dedup_key tests
# ────────────────────────────────────────────

class TestDedupKey:
    """Test _dedup_key weight syntax stripping."""

    def test_plain_tag(self):
        assert V3PromptBuilder._dedup_key("brown_hair") == "brown_hair"

    def test_weighted_tag(self):
        assert V3PromptBuilder._dedup_key("(1boy:1.3)") == "1boy"

    def test_high_precision_weight(self):
        assert V3PromptBuilder._dedup_key("(smile:0.85)") == "smile"

    def test_lora_tag_preserved(self):
        # LoRA tags contain colons but aren't simple weight syntax
        result = V3PromptBuilder._dedup_key("<lora:mymodel:0.7>")
        # Should strip < and split at first :
        assert "lora" in result

    def test_whitespace_stripped(self):
        assert V3PromptBuilder._dedup_key("  brown_hair  ") == "brown_hair"

    def test_case_insensitive(self):
        assert V3PromptBuilder._dedup_key("Brown_Hair") == "brown_hair"

    def test_nested_parens_not_weight(self):
        # Tag with parentheses but no weight format
        result = V3PromptBuilder._dedup_key("(smile)")
        # No colon → not weight syntax → keep as-is (with strip)
        assert result == "(smile)"


# ────────────────────────────────────────────
# _flatten_layers tests
# ────────────────────────────────────────────

class TestFlattenLayers:
    """Test _flatten_layers: dedup, BREAK, weight boost."""

    def test_basic_flatten(self, builder):
        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["masterpiece", "best_quality"]
        layers[LAYER_SUBJECT] = ["1girl"]
        layers[LAYER_ENVIRONMENT] = ["park", "outdoors"]

        result = builder._flatten_layers(layers)
        assert result == "masterpiece, best_quality, 1girl, park, outdoors"

    def test_cross_layer_dedup(self, builder):
        """Same tag in multiple layers → keep only first occurrence."""
        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["masterpiece"]
        layers[LAYER_SUBJECT] = ["1girl"]
        layers[LAYER_IDENTITY] = ["1girl"]  # Duplicate

        result = builder._flatten_layers(layers)
        tokens = [t.strip() for t in result.split(",")]
        assert tokens.count("1girl") == 1

    def test_weighted_dedup(self, builder):
        """(1boy:1.3) and 1boy should dedup to first occurrence."""
        layers = [[] for _ in range(12)]
        layers[LAYER_SUBJECT] = ["(1boy:1.3)"]
        layers[LAYER_IDENTITY] = ["1boy"]  # Duplicate (without weight)

        result = builder._flatten_layers(layers)
        tokens = [t.strip() for t in result.split(",")]
        assert "(1boy:1.3)" in tokens
        # Plain "1boy" should not appear separately
        assert tokens.count("(1boy:1.3)") == 1
        assert "1boy" not in tokens

    def test_break_insertion_with_lora(self, builder):
        """BREAK after L6 when character LoRA is active."""
        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["masterpiece"]
        layers[LAYER_SUBJECT] = ["1girl"]
        layers[LAYER_EXPRESSION] = ["smile"]

        result = builder._flatten_layers(layers, has_character_lora=True)
        tokens = [t.strip() for t in result.split(",")]
        assert "BREAK" in tokens
        # BREAK should come before expression tokens
        break_idx = tokens.index("BREAK")
        smile_idx = tokens.index("(smile:1.1)")
        assert break_idx < smile_idx

    def test_no_break_without_lora(self, builder):
        """No BREAK when no character LoRA."""
        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["masterpiece"]
        layers[LAYER_EXPRESSION] = ["smile"]

        result = builder._flatten_layers(layers, has_character_lora=False)
        assert "BREAK" not in result

    def test_expression_action_weight_boost(self, builder):
        """L7 (Expression) and L8 (Action) get :1.1 boost."""
        layers = [[] for _ in range(12)]
        layers[LAYER_EXPRESSION] = ["smile", "blush"]
        layers[LAYER_ACTION] = ["standing"]

        result = builder._flatten_layers(layers)
        assert "(smile:1.1)" in result
        assert "(blush:1.1)" in result
        assert "(standing:1.1)" in result

    def test_already_weighted_no_double_boost(self, builder):
        """Tags with existing weight should NOT get double-boosted."""
        layers = [[] for _ in range(12)]
        layers[LAYER_EXPRESSION] = ["(smile:0.8)"]

        result = builder._flatten_layers(layers)
        # Already has ":" so should be preserved as-is
        assert "(smile:0.8)" in result
        assert "((smile:0.8):1.1)" not in result

    def test_empty_layers_skipped(self, builder):
        """Empty layers produce no tokens."""
        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["masterpiece"]
        # All other layers empty

        result = builder._flatten_layers(layers)
        assert result == "masterpiece"


# ────────────────────────────────────────────
# Gender enhancement tests
# ────────────────────────────────────────────

class TestGenderEnhancement:
    """Test _apply_gender_enhancement for male character SD bias fix."""

    def _make_character(self, gender=None):
        char = MagicMock()
        char.gender = gender
        return char

    def test_male_character_gets_enhancement(self, builder):
        """Male character → enhancement tags in LAYER_SUBJECT."""
        char = self._make_character(gender="male")
        layers = [[] for _ in range(12)]
        layers[LAYER_SUBJECT] = ["1boy"]

        builder._apply_gender_enhancement(char, [], layers)

        assert "(1boy:1.3)" in layers[LAYER_SUBJECT]
        assert "(male_focus:1.2)" in layers[LAYER_SUBJECT]
        assert "(bishounen:1.1)" in layers[LAYER_SUBJECT]

    def test_female_character_no_enhancement(self, builder):
        """Female character → no enhancement tags."""
        char = self._make_character(gender="female")
        layers = [[] for _ in range(12)]
        layers[LAYER_SUBJECT] = ["1girl"]

        builder._apply_gender_enhancement(char, [], layers)

        assert "(1boy:1.3)" not in layers[LAYER_SUBJECT]
        assert "(male_focus:1.2)" not in layers[LAYER_SUBJECT]

    def test_no_gender_detects_from_tags(self, builder):
        """No gender field → detect from char_tags_data."""
        char = self._make_character(gender=None)
        char_tags = [{"name": "1boy", "layer": LAYER_SUBJECT, "weight": 1.0}]
        layers = [[] for _ in range(12)]

        builder._apply_gender_enhancement(char, char_tags, layers)

        assert "(1boy:1.3)" in layers[LAYER_SUBJECT]

    def test_no_gender_detects_female_from_tags(self, builder):
        """No gender field + 1girl tag → no enhancement."""
        char = self._make_character(gender=None)
        char_tags = [{"name": "1girl", "layer": LAYER_SUBJECT, "weight": 1.0}]
        layers = [[] for _ in range(12)]

        builder._apply_gender_enhancement(char, char_tags, layers)

        assert "(1boy:1.3)" not in layers[LAYER_SUBJECT]

    def test_no_gender_detects_from_layer_tokens(self, builder):
        """No gender field, no tags → detect from existing layer tokens."""
        char = self._make_character(gender=None)
        layers = [[] for _ in range(12)]
        layers[LAYER_SUBJECT] = ["1boy"]

        builder._apply_gender_enhancement(char, [], layers)

        assert "(1boy:1.3)" in layers[LAYER_SUBJECT]

    def test_no_duplicate_enhancement(self, builder):
        """Enhancement tags should not be added twice."""
        char = self._make_character(gender="male")
        layers = [[] for _ in range(12)]
        layers[LAYER_SUBJECT] = ["(1boy:1.3)"]  # Already present

        builder._apply_gender_enhancement(char, [], layers)

        # Count occurrences of the enhancement tag
        count = layers[LAYER_SUBJECT].count("(1boy:1.3)")
        assert count == 1
