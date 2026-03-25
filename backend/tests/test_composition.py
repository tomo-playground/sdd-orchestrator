"""Tests for PromptBuilder: _flatten_layers, _dedup_key, gender enhancement, conflict resolution."""

from unittest.mock import MagicMock, patch

import pytest

from config import CHARACTER_CAMERA_TAGS, EXCLUSIVE_TAG_GROUPS
from services.prompt.composition import (
    CHARACTER_ONLY_LAYERS,
    LAYER_ACCESSORY,
    LAYER_ACTION,
    LAYER_ATMOSPHERE,
    LAYER_BODY,
    LAYER_CAMERA,
    LAYER_ENVIRONMENT,
    LAYER_EXPRESSION,
    LAYER_IDENTITY,
    LAYER_MAIN_CLOTH,
    LAYER_NAMES,  # noqa: F401
    LAYER_QUALITY,
    LAYER_SUBJECT,
    PromptBuilder,
)


@pytest.fixture
def builder():
    """Create PromptBuilder with mocked DB session."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    return PromptBuilder(mock_db)


# ────────────────────────────────────────────
# _dedup_key tests
# ────────────────────────────────────────────


class TestDedupKey:
    """Test _dedup_key weight syntax stripping."""

    def test_plain_tag(self):
        assert PromptBuilder._dedup_key("brown_hair") == "brown_hair"

    def test_weighted_tag(self):
        assert PromptBuilder._dedup_key("(1boy:1.3)") == "1boy"

    def test_high_precision_weight(self):
        assert PromptBuilder._dedup_key("(smile:0.85)") == "smile"

    def test_lora_tag_preserved(self):
        # LoRA tags contain colons but aren't simple weight syntax
        result = PromptBuilder._dedup_key("<lora:mymodel:0.7>")
        # Should strip < and split at first :
        assert "lora" in result

    def test_whitespace_stripped(self):
        assert PromptBuilder._dedup_key("  brown_hair  ") == "brown_hair"

    def test_case_insensitive(self):
        assert PromptBuilder._dedup_key("Brown_Hair") == "brown_hair"

    def test_nested_parens_not_weight(self):
        # Tag with parentheses but no weight format
        result = PromptBuilder._dedup_key("(smile)")
        # No colon → not weight syntax → keep as-is (with strip)
        assert result == "(smile)"

    def test_space_underscore_normalized(self):
        """LoRA trigger word 'flat color' and tag 'flat_color' must produce same key."""
        assert PromptBuilder._dedup_key("flat color") == PromptBuilder._dedup_key("flat_color")
        assert PromptBuilder._dedup_key("flat color") == "flat_color"

    def test_space_underscore_multi_word(self):
        """Multi-word trigger words normalize to underscore."""
        assert PromptBuilder._dedup_key("anime coloring") == "anime_coloring"
        assert PromptBuilder._dedup_key("anime_coloring") == "anime_coloring"


class TestTriggerExistsInLayers:
    """Test _trigger_exists_in_layers cross-layer normalized check."""

    def test_exact_match(self):
        layers = [["flat_color"], [], []]
        assert PromptBuilder._trigger_exists_in_layers("flat_color", layers) is True

    def test_space_vs_underscore(self):
        """Trigger 'flat color' should match existing tag 'flat_color'."""
        layers = [["flat_color"], [], []]
        assert PromptBuilder._trigger_exists_in_layers("flat color", layers) is True

    def test_cross_layer(self):
        """Should search across all layers, not just target."""
        layers = [[], ["anime_coloring"], []]
        assert PromptBuilder._trigger_exists_in_layers("anime coloring", layers) is True

    def test_weighted_tag_match(self):
        """Trigger should match weighted tags like (flat_color:1.15)."""
        layers = [["(flat_color:1.15)"], [], []]
        assert PromptBuilder._trigger_exists_in_layers("flat color", layers) is True

    def test_no_match(self):
        layers = [["1girl"], ["smile"], []]
        assert PromptBuilder._trigger_exists_in_layers("flat color", layers) is False


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
        assert result == "masterpiece, best_quality, 1girl, (park:1.15), outdoors"

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

    def test_lora_weight_dedup(self, builder):
        """Same LoRA with different weights → keep only first occurrence."""
        layers = [[] for _ in range(12)]
        layers[LAYER_IDENTITY] = ["<lora:flat_color:0.6>"]
        layers[LAYER_ATMOSPHERE] = ["<lora:flat_color:0.76>"]

        result = builder._flatten_layers(layers)
        lora_count = result.count("<lora:flat_color:")
        assert lora_count == 1, f"Expected 1 flat_color LoRA, got {lora_count}: {result}"

    def test_trigger_word_tag_dedup(self, builder):
        """LoRA trigger 'flat color' and tag 'flat_color' → keep only first (tag)."""
        layers = [[] for _ in range(12)]
        layers[LAYER_SUBJECT] = ["flat_color"]  # Danbooru tag (underscore)
        layers[LAYER_ATMOSPHERE] = ["flat color", "<lora:flat_color:0.4>"]  # Trigger (space)

        result = builder._flatten_layers(layers)
        # "flat_color" tag survives (first occurrence), "flat color" trigger is deduped
        assert "flat_color" in result
        assert ", flat color," not in result  # Trigger word should be deduped
        assert "<lora:flat_color:0.4>" in result  # LoRA tag itself is different

    def test_no_break_in_single_context(self, builder):
        """BREAK is never inserted - single context for better scene control."""
        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["masterpiece"]
        layers[LAYER_SUBJECT] = ["1girl"]
        layers[LAYER_EXPRESSION] = ["smile"]
        layers[LAYER_ACTION] = ["standing"]
        layers[LAYER_ENVIRONMENT] = ["park", "outdoors"]

        result = builder._flatten_layers(layers)
        assert "BREAK" not in result
        # All tokens in single context
        assert "masterpiece" in result
        assert "(smile:1.2)" in result
        assert "park" in result

    def test_expression_action_weight_boost(self, builder):
        """L7 (Expression) and L8 (Action) get :1.2 boost."""
        layers = [[] for _ in range(12)]
        layers[LAYER_EXPRESSION] = ["smile", "blush"]
        layers[LAYER_ACTION] = ["standing"]

        result = builder._flatten_layers(layers)
        assert "(smile:1.2)" in result
        assert "(blush:1.2)" in result
        assert "(standing:1.2)" in result

    def test_already_weighted_no_double_boost(self, builder):
        """Tags with existing weight should NOT get double-boosted."""
        layers = [[] for _ in range(12)]
        layers[LAYER_EXPRESSION] = ["(smile:0.8)"]

        result = builder._flatten_layers(layers)
        # Already has ":" so should be preserved as-is
        assert "(smile:0.8)" in result
        assert "((smile:0.8):1.2)" not in result

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

    def test_male_removes_conflicting_female_tags(self, builder):
        """Male character → removes 1girl from LAYER_SUBJECT."""
        char = self._make_character(gender="male")
        layers = [[] for _ in range(12)]
        layers[LAYER_SUBJECT] = ["1girl", "solo"]

        builder._apply_gender_enhancement(char, [], layers)

        assert "1girl" not in layers[LAYER_SUBJECT]
        assert "solo" in layers[LAYER_SUBJECT]
        assert "(1boy:1.3)" in layers[LAYER_SUBJECT]

    def test_male_removes_weighted_female_tags(self, builder):
        """Male character → removes (1girl:1.0) weighted variant too."""
        char = self._make_character(gender="male")
        layers = [[] for _ in range(12)]
        layers[LAYER_SUBJECT] = ["(1girl:1.0)", "solo"]

        builder._apply_gender_enhancement(char, [], layers)

        assert "(1girl:1.0)" not in layers[LAYER_SUBJECT]
        assert "(1boy:1.3)" in layers[LAYER_SUBJECT]

    def test_female_character_keeps_female_tags(self, builder):
        """Female character → 1girl NOT removed."""
        char = self._make_character(gender="female")
        layers = [[] for _ in range(12)]
        layers[LAYER_SUBJECT] = ["1girl"]

        builder._apply_gender_enhancement(char, [], layers)

        assert "1girl" in layers[LAYER_SUBJECT]
        assert "(1boy:1.3)" not in layers[LAYER_SUBJECT]


# ────────────────────────────────────────────
# D-2: TagRuleCache conflict resolution tests
# ────────────────────────────────────────────


class TestConflictResolution:
    """Test TagRuleCache integration in _flatten_layers (D-2)."""

    @patch("services.prompt.composition.TagRuleCache")
    def test_conflicting_tags_removed(self, mock_cache, builder):
        """When two tags conflict, keep first occurrence only."""
        # Mock conflict: brown_hair vs blonde_hair
        mock_cache.initialize.return_value = None
        mock_cache.is_conflicting.side_effect = lambda t1, t2: (
            (t1 == "blonde_hair" and t2 == "brown_hair") or (t1 == "brown_hair" and t2 == "blonde_hair")
        )

        layers = [[] for _ in range(12)]
        layers[LAYER_IDENTITY] = ["brown_hair", "blonde_hair"]

        result = builder._flatten_layers(layers)
        tokens = [t.strip() for t in result.split(",")]

        # Only first tag (brown_hair) should remain
        assert "brown_hair" in tokens
        assert "blonde_hair" not in tokens

    @patch("services.prompt.composition.TagRuleCache")
    def test_no_conflict_both_kept(self, mock_cache, builder):
        """Non-conflicting tags should both be kept."""
        mock_cache.initialize.return_value = None
        mock_cache.is_conflicting.return_value = False

        layers = [[] for _ in range(12)]
        layers[LAYER_IDENTITY] = ["brown_hair", "long_hair"]

        result = builder._flatten_layers(layers)
        tokens = [t.strip() for t in result.split(",")]

        assert "brown_hair" in tokens
        assert "long_hair" in tokens


# ────────────────────────────────────────────
# D-3: TagFilterCache restricted tags tests
# ────────────────────────────────────────────


class TestRestrictedTags:
    """Test TagFilterCache integration (D-3)."""

    @patch("services.prompt.composition.TagFilterCache")
    def test_restricted_tags_filtered(self, mock_cache, builder):
        """Restricted tags should be filtered from positive_prompt."""
        from unittest.mock import MagicMock

        mock_cache.initialize.return_value = None
        mock_cache.is_restricted.side_effect = lambda tag: tag.lower() in {"kitchen", "outdoors"}

        # Mock character with positive_prompt containing restricted tags
        char = MagicMock()
        char.id = 1
        char.gender = "female"
        char.positive_prompt = "brown_hair, kitchen, long_hair, outdoors"
        char.tags = []
        char.loras = []

        # Mock DB queries
        builder.db.query.return_value.filter.return_value.first.return_value = char

        result = builder.compose_for_character(character_id=1, scene_tags=["sitting"])

        # kitchen and outdoors should be filtered out
        assert "kitchen" not in result
        assert "outdoors" not in result
        assert "brown_hair" in result or "long_hair" in result  # Valid tags kept


# ────────────────────────────────────────────
# D-4: Pattern-based fallback tests
# ────────────────────────────────────────────


class TestPatternBasedFallback:
    """Test _infer_layer_from_pattern for DB-missing tags (D-4)."""

    def test_hair_pattern_to_identity(self):
        """*_hair tags → LAYER_IDENTITY."""
        assert PromptBuilder._infer_layer_from_pattern("pink_hair") == LAYER_IDENTITY
        assert PromptBuilder._infer_layer_from_pattern("short_hair") == LAYER_IDENTITY

    def test_eyes_pattern_to_identity(self):
        """*_eyes tags → LAYER_IDENTITY."""
        assert PromptBuilder._infer_layer_from_pattern("blue_eyes") == LAYER_IDENTITY
        assert PromptBuilder._infer_layer_from_pattern("red_eyes") == LAYER_IDENTITY

    def test_action_pattern(self):
        """*ing tags → LAYER_ACTION."""
        assert PromptBuilder._infer_layer_from_pattern("running") == LAYER_ACTION
        assert PromptBuilder._infer_layer_from_pattern("walking") == LAYER_ACTION

    def test_action_pattern_excludes_earring(self):
        """earring should NOT be classified as action."""
        # "ring" ending should exclude -ring suffix
        result = PromptBuilder._infer_layer_from_pattern("earring")
        # earring should fall to LAYER_SUBJECT (default)
        assert result == LAYER_SUBJECT

    def test_camera_shot_pattern(self):
        """*_shot, *_view, from_* → LAYER_CAMERA."""
        assert PromptBuilder._infer_layer_from_pattern("wide_shot") == LAYER_CAMERA
        assert PromptBuilder._infer_layer_from_pattern("top_view") == LAYER_CAMERA
        assert PromptBuilder._infer_layer_from_pattern("from_above") == LAYER_CAMERA

    def test_expression_keywords(self):
        """Known expression keywords → LAYER_EXPRESSION."""
        assert PromptBuilder._infer_layer_from_pattern("smiling") == LAYER_EXPRESSION
        assert PromptBuilder._infer_layer_from_pattern("crying") == LAYER_EXPRESSION

    def test_background_suffix_to_environment(self):
        """*_background tags → LAYER_ENVIRONMENT."""
        assert PromptBuilder._infer_layer_from_pattern("machine_background") == LAYER_ENVIRONMENT
        assert PromptBuilder._infer_layer_from_pattern("mechanical_background") == LAYER_ENVIRONMENT

    def test_location_keywords_to_environment(self):
        """Known location keywords → LAYER_ENVIRONMENT."""
        assert PromptBuilder._infer_layer_from_pattern("laboratory") == LAYER_ENVIRONMENT
        assert PromptBuilder._infer_layer_from_pattern("lab") == LAYER_ENVIRONMENT
        assert PromptBuilder._infer_layer_from_pattern("space") == LAYER_ENVIRONMENT

    def test_room_suffix_to_environment(self):
        """*_room tags → LAYER_ENVIRONMENT."""
        assert PromptBuilder._infer_layer_from_pattern("server_room") == LAYER_ENVIRONMENT

    def test_mood_keywords_to_atmosphere(self):
        """Mood/genre keywords → LAYER_ATMOSPHERE."""
        assert PromptBuilder._infer_layer_from_pattern("futuristic") == LAYER_ATMOSPHERE
        assert PromptBuilder._infer_layer_from_pattern("cyberpunk") == LAYER_ATMOSPHERE
        assert PromptBuilder._infer_layer_from_pattern("steampunk") == LAYER_ATMOSPHERE

    def test_unknown_tag_defaults_to_subject(self):
        """Unknown pattern → LAYER_SUBJECT."""
        assert PromptBuilder._infer_layer_from_pattern("unknown_tag") == LAYER_SUBJECT
        assert PromptBuilder._infer_layer_from_pattern("mystery") == LAYER_SUBJECT


# ────────────────────────────────────────────
# Exclusive group filtering tests
# ────────────────────────────────────────────


def _make_tag_info(_name: str, layer: int = LAYER_IDENTITY, group: str | None = None) -> dict:
    """Helper to build tag info dict."""
    return {"layer": layer, "scope": "ANY", "group_name": group}


class TestBuildCharOccupiedGroups:
    """Test _build_char_occupied_groups identifies occupied exclusive groups."""

    def test_hair_color_occupied(self, builder):
        builder.get_tag_info = MagicMock(
            return_value={
                "red_hair": _make_tag_info("red_hair", group="hair_color"),
            }
        )
        result = builder._build_char_occupied_groups([{"name": "red_hair", "layer": 2, "weight": 1.0}])
        assert "hair_color" in result

    def test_multiple_groups(self, builder):
        builder.get_tag_info = MagicMock(
            return_value={
                "red_hair": _make_tag_info("red_hair", group="hair_color"),
                "blue_eyes": _make_tag_info("blue_eyes", group="eye_color"),
            }
        )
        char_tags = [
            {"name": "red_hair", "layer": 2, "weight": 1.0},
            {"name": "blue_eyes", "layer": 2, "weight": 1.0},
        ]
        result = builder._build_char_occupied_groups(char_tags)
        assert result == {"hair_color", "eye_color"}

    def test_non_exclusive_group_ignored(self, builder):
        builder.get_tag_info = MagicMock(
            return_value={
                "messy_hair": _make_tag_info("messy_hair", group="hair_style"),
            }
        )
        result = builder._build_char_occupied_groups([{"name": "messy_hair", "layer": 2, "weight": 1.0}])
        assert len(result) == 0

    def test_empty_char_tags(self, builder):
        result = builder._build_char_occupied_groups([])
        assert result == set()

    def test_no_group_name(self, builder):
        builder.get_tag_info = MagicMock(
            return_value={
                "1girl": _make_tag_info("1girl", group="subject"),
            }
        )
        result = builder._build_char_occupied_groups([{"name": "1girl", "layer": 1, "weight": 1.0}])
        assert len(result) == 0


class TestDistributeTags:
    """Test _distribute_tags filters scene tags from occupied exclusive groups."""

    def _setup_tag_info(self, builder, char_info: dict, scene_info: dict):
        """Mock get_tag_info to return different results for char vs scene tags."""
        all_info = {**char_info, **scene_info}
        builder.get_tag_info = MagicMock(
            side_effect=lambda names: {
                n: all_info[n] for n in [t.lower().replace(" ", "_").strip() for t in names] if n in all_info
            }
        )

    def test_hair_color_conflict_drops_scene_tag(self, builder):
        """Char red_hair + scene brown_hair → brown_hair dropped."""
        char_info = {"red_hair": _make_tag_info("red_hair", group="hair_color")}
        scene_info = {
            "brown_hair": _make_tag_info("brown_hair", group="hair_color"),
            "outdoors": _make_tag_info("outdoors", LAYER_ENVIRONMENT, group="location"),
        }
        self._setup_tag_info(builder, char_info, scene_info)

        char_tags = [{"name": "red_hair", "layer": LAYER_IDENTITY, "weight": 1.0}]
        scene_tags = ["brown_hair", "outdoors"]
        scene_tag_info = dict(scene_info)
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, scene_tags, scene_tag_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "red_hair" in all_tokens
        assert "brown_hair" not in all_tokens
        assert "outdoors" in all_tokens

    def test_eye_color_conflict_drops_scene_tag(self, builder):
        """Char purple_eyes + scene brown_eyes → brown_eyes dropped."""
        char_info = {"purple_eyes": _make_tag_info("purple_eyes", group="eye_color")}
        scene_info = {"brown_eyes": _make_tag_info("brown_eyes", group="eye_color")}
        self._setup_tag_info(builder, char_info, scene_info)

        char_tags = [{"name": "purple_eyes", "layer": LAYER_IDENTITY, "weight": 1.0}]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["brown_eyes"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "purple_eyes" in all_tokens
        assert "brown_eyes" not in all_tokens

    def test_no_char_tag_keeps_scene_tag(self, builder):
        """No char hair tag → scene brown_hair kept."""
        char_info = {"1girl": _make_tag_info("1girl", group="subject")}
        scene_info = {"brown_hair": _make_tag_info("brown_hair", group="hair_color")}
        self._setup_tag_info(builder, char_info, scene_info)

        char_tags = [{"name": "1girl", "layer": LAYER_SUBJECT, "weight": 1.0}]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["brown_hair"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "brown_hair" in all_tokens

    def test_non_exclusive_group_not_filtered(self, builder):
        """Char messy_hair (hair_style) + scene ponytail → both kept."""
        char_info = {"messy_hair": _make_tag_info("messy_hair", group="hair_style")}
        scene_info = {"ponytail": _make_tag_info("ponytail", group="hair_style")}
        self._setup_tag_info(builder, char_info, scene_info)

        char_tags = [{"name": "messy_hair", "layer": LAYER_IDENTITY, "weight": 1.0}]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["ponytail"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "messy_hair" in all_tokens
        assert "ponytail" in all_tokens

    def test_multiple_groups_filtered(self, builder):
        """Char red_hair + blue_eyes → scene brown_hair + green_eyes dropped."""
        char_info = {
            "red_hair": _make_tag_info("red_hair", group="hair_color"),
            "blue_eyes": _make_tag_info("blue_eyes", group="eye_color"),
        }
        scene_info = {
            "brown_hair": _make_tag_info("brown_hair", group="hair_color"),
            "green_eyes": _make_tag_info("green_eyes", group="eye_color"),
            "standing": _make_tag_info("standing", LAYER_ACTION, group="pose"),
        }
        self._setup_tag_info(builder, char_info, scene_info)

        char_tags = [
            {"name": "red_hair", "layer": LAYER_IDENTITY, "weight": 1.0},
            {"name": "blue_eyes", "layer": LAYER_IDENTITY, "weight": 1.0},
        ]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["brown_hair", "green_eyes", "standing"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "red_hair" in all_tokens
        assert "blue_eyes" in all_tokens
        assert "brown_hair" not in all_tokens
        assert "green_eyes" not in all_tokens
        assert "standing" in all_tokens

    def test_weighted_char_tag_occupies_group(self, builder):
        """Char (red_hair:0.8) still occupies hair_color group."""
        char_info = {"red_hair": _make_tag_info("red_hair", group="hair_color")}
        scene_info = {"brown_hair": _make_tag_info("brown_hair", group="hair_color")}
        self._setup_tag_info(builder, char_info, scene_info)

        char_tags = [{"name": "red_hair", "layer": LAYER_IDENTITY, "weight": 0.8}]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["brown_hair"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "(red_hair:0.8)" in all_tokens
        assert "brown_hair" not in all_tokens

    def test_scene_tag_without_group_always_passes(self, builder):
        """Scene tags with group_name=None always pass through."""
        char_info = {"red_hair": _make_tag_info("red_hair", group="hair_color")}
        scene_info = {"unknown_tag": _make_tag_info("unknown_tag", LAYER_SUBJECT, group=None)}
        self._setup_tag_info(builder, char_info, scene_info)

        char_tags = [{"name": "red_hair", "layer": LAYER_IDENTITY, "weight": 1.0}]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["unknown_tag"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "unknown_tag" in all_tokens

    def test_skin_color_conflict(self, builder):
        """Char pale_skin + scene dark_skin → dark_skin dropped."""
        char_info = {"pale_skin": _make_tag_info("pale_skin", group="skin_color")}
        scene_info = {"dark_skin": _make_tag_info("dark_skin", group="skin_color")}
        self._setup_tag_info(builder, char_info, scene_info)

        char_tags = [{"name": "pale_skin", "layer": LAYER_IDENTITY, "weight": 1.0}]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["dark_skin"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "pale_skin" in all_tokens
        assert "dark_skin" not in all_tokens

    def test_lora_tags_in_scene_tags_are_stripped(self, builder):
        """LoRA tags in scene_tags must be stripped to prevent double injection."""
        scene_info = {"outdoors": _make_tag_info("outdoors", LAYER_ENVIRONMENT)}
        builder.get_tag_info = MagicMock(
            side_effect=lambda names: {
                n: scene_info[n] for n in [t.lower().replace(" ", "_").strip() for t in names] if n in scene_info
            }
        )

        char_tags = [{"name": "1girl", "layer": LAYER_SUBJECT, "weight": 1.0}]
        scene_tags = ["outdoors", "<lora:flat_color:0.76>", "flat color"]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, scene_tags, scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "outdoors" in all_tokens
        assert "flat color" in all_tokens
        # LoRA tag must NOT appear — _inject_loras handles LoRA injection
        lora_tokens = [t for t in all_tokens if "<lora:" in t]
        assert lora_tokens == [], f"LoRA tags must be stripped from scene_tags: {lora_tokens}"


class TestExclusiveGroupsConstant:
    """Verify EXCLUSIVE_TAG_GROUPS contains expected groups."""

    def test_contains_expected_groups(self):
        assert "hair_color" in EXCLUSIVE_TAG_GROUPS
        assert "eye_color" in EXCLUSIVE_TAG_GROUPS
        assert "hair_length" in EXCLUSIVE_TAG_GROUPS
        assert "skin_color" in EXCLUSIVE_TAG_GROUPS
        assert "clothing" in EXCLUSIVE_TAG_GROUPS
        assert "accessory" in EXCLUSIVE_TAG_GROUPS

    def test_does_not_contain_hair_style(self):
        assert "hair_style" not in EXCLUSIVE_TAG_GROUPS


# ────────────────────────────────────────────
# _inject_loras dedup tests
# ────────────────────────────────────────────


class TestInjectLorasDedup:
    """Test _inject_loras dedup: scene-triggered + style_loras with same name."""

    @patch("services.prompt.composition.LoRATriggerCache")
    def test_inject_loras_no_duplicate_style_lora(self, mock_trigger_cache, builder):
        """Scene-triggered + style_loras with same name → only one <lora:> tag."""
        # Scene tag "flat_color" triggers LoRA via cache
        mock_trigger_cache.get_lora_name.side_effect = lambda tag: "flat_color" if tag == "flat_color" else None

        # Mock _get_lora_info for scene-triggered lookup
        from services.prompt.composition import LoRAInfo

        builder._get_lora_info = MagicMock(return_value=LoRAInfo(0.6, "style", []))

        character = MagicMock()
        character.loras = []

        layers = [[] for _ in range(12)]
        scene_tags = ["flat_color", "outdoors"]

        # style_loras also includes flat_color (would be duplicate)
        style_loras = [{"name": "flat_color", "weight": 0.6, "trigger_words": []}]

        builder._inject_loras(character, scene_tags, layers, style_loras)

        # Count lora tags across all layers
        all_tokens = [t for layer in layers for t in layer]
        lora_count = sum(1 for t in all_tokens if "<lora:flat_color:" in t)
        assert lora_count == 1, f"Expected 1 flat_color LoRA tag, got {lora_count}: {all_tokens}"

    @patch("services.prompt.composition.LoRATriggerCache")
    def test_inject_loras_style_lora_added_when_not_triggered(self, mock_trigger_cache, builder):
        """style_loras not in scene tags → still added normally."""
        mock_trigger_cache.get_lora_name.return_value = None

        character = MagicMock()
        character.loras = []

        layers = [[] for _ in range(12)]
        scene_tags = ["outdoors", "standing"]

        # flat_color only in style_loras, not triggered by scene
        style_loras = [{"name": "flat_color", "weight": 0.7, "trigger_words": ["flat color"]}]

        builder._inject_loras(character, scene_tags, layers, style_loras)

        atmo_tokens = layers[LAYER_ATMOSPHERE]
        assert "<lora:flat_color:0.7>" in atmo_tokens
        assert "flat color" in atmo_tokens


# ────────────────────────────────────────────
# Background scene filtering tests
# ────────────────────────────────────────────


class TestBackgroundSceneFiltering:
    """Test background scene detection and character tag stripping."""

    def test_is_background_scene_detection(self):
        """no_humans tag triggers background scene detection."""
        assert PromptBuilder._is_background_scene(["no_humans", "scenery", "cafe"])
        assert PromptBuilder._is_background_scene(["scenery", "no_humans"])
        # Case/whitespace insensitive
        assert PromptBuilder._is_background_scene(["No_Humans", "park"])
        assert PromptBuilder._is_background_scene(["no humans", "park"])

    def test_is_background_scene_negative(self):
        """Scenes without no_humans are not background scenes."""
        assert not PromptBuilder._is_background_scene(["1girl", "standing", "cafe"])
        assert not PromptBuilder._is_background_scene(["scenery", "outdoors"])
        assert not PromptBuilder._is_background_scene([])

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_compose_background_strips_character_tags(self, mock_alias, mock_rule, builder):
        """Background compose removes standing/cooking/smiling but keeps environment."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...  # No alias — keep original
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        # Mock tag DB to return proper layers
        builder.get_tag_info = MagicMock(
            return_value={
                "no_humans": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
                "scenery": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
                "cafe": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
                "standing": {"layer": LAYER_ACTION, "scope": "ANY", "group_name": None},
                "cooking": {"layer": LAYER_ACTION, "scope": "ANY", "group_name": None},
                "cowboy_shot": {"layer": LAYER_CAMERA, "scope": "ANY", "group_name": None},
                "night": {"layer": LAYER_ATMOSPHERE, "scope": "ANY", "group_name": None},
            }
        )

        result = builder._compose_background_scene(
            ["no_humans", "scenery", "cafe", "standing", "cooking", "cowboy_shot", "night"]
        )

        # Character tags stripped
        assert "standing" not in result
        assert "cooking" not in result
        assert "cowboy_shot" not in result

        # Environment/atmosphere tags kept
        assert "no_humans" in result
        assert "scenery" in result
        assert "cafe" in result
        assert "night" in result

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_compose_for_character_strips_no_humans_and_composes(self, mock_alias, mock_rule, builder):
        """compose_for_character strips no_humans when character_id is set."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        # Mock tag DB to return proper layers
        builder.get_tag_info = MagicMock(
            return_value={
                "scenery": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
                "library": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
            }
        )

        # Mock Character query to return None (fallback to generic compose)
        builder.db.query.return_value.filter.return_value.first.return_value = None

        result = builder.compose_for_character(
            character_id=999,
            scene_tags=["no_humans", "scenery", "library"],
        )

        # no_humans stripped — character_id takes priority over tag content
        assert "no_humans" not in result
        assert "library" in result

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_background_scene_keeps_style_lora_tag_strips_trigger(self, mock_alias, mock_rule, builder):
        """Background scene keeps LoRA tag but strips trigger words to avoid human bias."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        style_loras = [{"name": "flat_color", "weight": 0.6, "trigger_words": ["flat color"]}]

        result = builder._compose_background_scene(
            ["no_humans", "scenery", "cafe"],
            style_loras=style_loras,
        )

        assert "<lora:flat_color:0.6>" in result
        # Trigger word stripped — may bias SD toward character generation
        assert "flat color" not in result

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_background_scene_keeps_no_humans(self, mock_alias, mock_rule, builder):
        """no_humans tag is always present in final background prompt."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        result = builder._compose_background_scene(["scenery", "cafe", "no_humans"])
        assert "no_humans" in result

    def test_strip_character_layers(self):
        """_strip_character_layers clears layers 1-8 and character camera tags."""
        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["masterpiece"]
        layers[LAYER_SUBJECT] = ["1girl"]
        layers[LAYER_IDENTITY] = ["brown_hair"]
        layers[LAYER_ACTION] = ["standing"]
        layers[LAYER_CAMERA] = ["cowboy_shot", "from_above"]
        layers[LAYER_ENVIRONMENT] = ["cafe", "no_humans"]

        PromptBuilder._strip_character_layers(layers)

        # Character layers cleared
        assert layers[LAYER_SUBJECT] == []
        assert layers[LAYER_IDENTITY] == []
        assert layers[LAYER_ACTION] == []

        # Character camera tags stripped, non-character kept
        assert "cowboy_shot" not in layers[LAYER_CAMERA]
        assert "from_above" in layers[LAYER_CAMERA]

        # Non-character layers untouched
        assert layers[LAYER_QUALITY] == ["masterpiece"]
        assert "cafe" in layers[LAYER_ENVIRONMENT]

    def test_character_only_layers_constant(self):
        """CHARACTER_ONLY_LAYERS covers layers 1-8 (SUBJECT through ACTION)."""
        assert CHARACTER_ONLY_LAYERS == frozenset({1, 2, 3, 4, 5, 6, 7, 8})

    def test_character_camera_tags_constant(self):
        """CHARACTER_CAMERA_TAGS contains expected framing tags."""
        expected = {"cowboy_shot", "upper_body", "portrait", "close-up", "close_up", "full_body"}
        assert expected.issubset(CHARACTER_CAMERA_TAGS)

    @patch("services.prompt.composition.LoRATriggerCache")
    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_compose_generic_background_strips_character_loras(self, mock_alias, mock_rule, mock_trigger, builder):
        """compose() with no_humans + character_loras → character LoRAs stripped."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False
        mock_trigger.get_lora_name.return_value = None

        builder.get_tag_info = MagicMock(
            return_value={
                "no_humans": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
                "scenery": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
            }
        )

        result = builder.compose(
            tags=["no_humans", "scenery"],
            character_loras=[{"name": "char_lora", "weight": 0.7, "trigger_words": ["trigger1"]}],
        )

        # Character LoRA and trigger should be stripped
        assert "char_lora" not in result
        assert "trigger1" not in result
        # Environment kept
        assert "no_humans" in result
        assert "scenery" in result

    @patch("services.prompt.composition.LoRATriggerCache")
    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_compose_background_strips_style_trigger_keeps_lora_tag(self, mock_alias, mock_rule, mock_trigger, builder):
        """compose() with no_humans: style LoRA tag kept, trigger word stripped."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False
        mock_trigger.get_lora_name.return_value = None

        builder.get_tag_info = MagicMock(
            return_value={
                "no_humans": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
                "beach": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
            }
        )

        result = builder.compose(
            tags=["no_humans", "beach"],
            character_loras=[{"name": "eureka_v9", "weight": 0.7, "trigger_words": ["eureka_style"]}],
            style_loras=[{"name": "flat_color", "weight": 0.6, "trigger_words": ["flat color"]}],
        )

        # Character LoRA fully stripped
        assert "eureka_v9" not in result
        assert "eureka_style" not in result
        # Style LoRA tag kept, trigger word stripped
        assert "<lora:flat_color:0.6>" in result
        assert "flat color" not in result


# ────────────────────────────────────────────
# LoRA Weight Cap tests
# ────────────────────────────────────────────


class TestLoRAWeightCap:
    """Test STYLE_LORA_WEIGHT_CAP applied at prompt composition time (SSOT)."""

    @patch("services.prompt.composition.LoRATriggerCache")
    def test_cap_applied_to_character_lora(self, mock_trigger_cache, builder):
        """Character LoRA weight 0.89 → capped to 0.76."""
        mock_trigger_cache.get_lora_name.return_value = None

        character = MagicMock()
        lora_obj = MagicMock()
        lora_obj.name = "char_lora"
        lora_obj.lora_type = "character"
        lora_obj.trigger_words = []
        builder.db.query.return_value.filter.return_value.first.return_value = lora_obj
        builder.get_effective_lora_weight = MagicMock(return_value=0.89)

        character.loras = [{"lora_id": 1, "weight": 0.89}]

        layers = [[] for _ in range(12)]
        builder._inject_loras(character, [], layers, None)

        all_tokens = [t for layer in layers for t in layer]
        # 0.89 × SCENE_CHARACTER_LORA_SCALE(0.45) = 0.4 (scaled before cap)
        assert "<lora:char_lora:0.4>" in all_tokens
        assert "<lora:char_lora:0.89>" not in all_tokens

    @patch("services.prompt.composition.LoRATriggerCache")
    def test_cap_applied_to_style_lora(self, mock_trigger_cache, builder):
        """Style LoRA weight 0.9 → capped to 0.76."""
        mock_trigger_cache.get_lora_name.return_value = None

        character = MagicMock()
        character.loras = []

        layers = [[] for _ in range(12)]
        style_loras = [{"name": "style_lora", "weight": 0.9, "trigger_words": []}]

        builder._inject_loras(character, [], layers, style_loras)

        all_tokens = [t for layer in layers for t in layer]
        assert "<lora:style_lora:0.76>" in all_tokens
        assert "<lora:style_lora:0.9>" not in all_tokens

    @patch("services.prompt.composition.LoRATriggerCache")
    def test_cap_applied_to_scene_triggered_lora(self, mock_trigger_cache, builder):
        """Scene-triggered LoRA weight 0.85 → capped to 0.76."""
        mock_trigger_cache.get_lora_name.side_effect = lambda tag: "scene_lora" if tag == "trigger_tag" else None
        from services.prompt.composition import LoRAInfo

        builder._get_lora_info = MagicMock(return_value=LoRAInfo(0.85, "character", []))

        character = MagicMock()
        character.loras = []

        layers = [[] for _ in range(12)]
        builder._inject_loras(character, ["trigger_tag"], layers, None)

        all_tokens = [t for layer in layers for t in layer]
        assert "<lora:scene_lora:0.76>" in all_tokens
        assert "<lora:scene_lora:0.85>" not in all_tokens

    @patch("services.prompt.composition.LoRATriggerCache")
    def test_weight_below_cap_preserved(self, mock_trigger_cache, builder):
        """Weight 0.65 (below cap) → preserved as-is."""
        mock_trigger_cache.get_lora_name.return_value = None

        character = MagicMock()
        character.loras = []

        layers = [[] for _ in range(12)]
        style_loras = [{"name": "mild_lora", "weight": 0.65, "trigger_words": []}]

        builder._inject_loras(character, [], layers, style_loras)

        all_tokens = [t for layer in layers for t in layer]
        assert "<lora:mild_lora:0.65>" in all_tokens

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_cap_in_compose_background_scene(self, mock_alias, mock_rule, builder):
        """Background scene style LoRA 0.9 → capped to 0.76."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        builder.get_tag_info = MagicMock(
            return_value={
                "no_humans": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
                "scenery": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
            }
        )

        style_loras = [{"name": "style_lora", "weight": 0.9, "trigger_words": []}]

        result = builder._compose_background_scene(
            ["no_humans", "scenery"],
            style_loras=style_loras,
        )

        assert "<lora:style_lora:0.76>" in result
        assert "<lora:style_lora:0.9>" not in result

    @patch("services.prompt.composition.LoRATriggerCache")
    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_cap_in_compose_generic(self, mock_alias, mock_rule, mock_trigger, builder):
        """compose() character_loras weight 0.89 → capped to 0.76."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False
        mock_trigger.get_lora_name.return_value = None

        builder.get_tag_info = MagicMock(
            return_value={
                "1girl": {"layer": LAYER_SUBJECT, "scope": "ANY", "group_name": None},
            }
        )

        result = builder.compose(
            tags=["1girl"],
            character_loras=[{"name": "char_lora", "weight": 0.89, "trigger_words": []}],
        )

        assert "<lora:char_lora:0.76>" in result
        assert "<lora:char_lora:0.89>" not in result

    def test_default_weight_not_capped(self):
        """DEFAULT_LORA_WEIGHT=0.7 < 0.76 → stays 0.7."""
        assert PromptBuilder._cap_lora_weight(0.7) == 0.7

    def test_cap_static_method(self):
        """_cap_lora_weight caps at STYLE_LORA_WEIGHT_CAP."""
        assert PromptBuilder._cap_lora_weight(0.89) == 0.76
        assert PromptBuilder._cap_lora_weight(0.76) == 0.76
        assert PromptBuilder._cap_lora_weight(0.5) == 0.5


# ────────────────────────────────────────────
# _apply_scene_character_actions tests
# ────────────────────────────────────────────


class TestApplySceneCharacterActions:
    """Test scene-level character action overrides on LAYER_EXPRESSION/LAYER_ACTION."""

    # layer → group_name 매핑 (테스트용)
    _LAYER_TO_GROUP = {7: "expression", 8: "pose", 10: "environment", 11: "mood"}

    def _seed_tags(self, db_session, names_layers: list[tuple[str, int]]):
        """Insert tags into DB and return {name: id}."""
        from models.tag import Tag

        result = {}
        for name, layer in names_layers:
            group = self._LAYER_TO_GROUP.get(layer, "subject")
            tag = Tag(name=name, category="scene", group_name=group)
            db_session.add(tag)
        db_session.flush()
        for name, _ in names_layers:
            tag = db_session.query(Tag).filter(Tag.name == name).one()
            result[name] = tag.id
        return result

    def test_overrides_expression_layer(self, db_session):
        """Scene actions should clear LAYER_EXPRESSION and inject new tags."""
        tag_ids = self._seed_tags(db_session, [("crying", LAYER_EXPRESSION)])
        builder = PromptBuilder(db_session)

        layers = [[] for _ in range(12)]
        layers[LAYER_EXPRESSION] = ["smile", "blush"]  # character defaults

        actions = [{"character_id": 10, "tag_id": tag_ids["crying"], "weight": 1.0}]
        builder._apply_scene_character_actions(10, actions, layers)

        assert layers[LAYER_EXPRESSION] == ["crying"]
        assert "smile" not in layers[LAYER_EXPRESSION]
        assert "blush" not in layers[LAYER_EXPRESSION]

    def test_overrides_action_layer(self, db_session):
        """Scene actions should clear LAYER_ACTION and inject new tags."""
        tag_ids = self._seed_tags(db_session, [("sitting", LAYER_ACTION)])
        builder = PromptBuilder(db_session)

        layers = [[] for _ in range(12)]
        layers[LAYER_ACTION] = ["standing"]

        actions = [{"character_id": 5, "tag_id": tag_ids["sitting"], "weight": 1.0}]
        builder._apply_scene_character_actions(5, actions, layers)

        assert layers[LAYER_ACTION] == ["sitting"]

    def test_weighted_tag_format(self, db_session):
        """Weight != 1.0 → (tag_name:weight) format."""
        tag_ids = self._seed_tags(db_session, [("angry", LAYER_EXPRESSION)])
        builder = PromptBuilder(db_session)

        layers = [[] for _ in range(12)]
        actions = [{"character_id": 1, "tag_id": tag_ids["angry"], "weight": 0.8}]
        builder._apply_scene_character_actions(1, actions, layers)

        assert "(angry:0.8)" in layers[LAYER_EXPRESSION]

    def test_filters_by_character_id(self, db_session):
        """Actions for other characters should be ignored."""
        tag_ids = self._seed_tags(db_session, [("smile", LAYER_EXPRESSION)])
        builder = PromptBuilder(db_session)

        layers = [[] for _ in range(12)]
        actions = [{"character_id": 99, "tag_id": tag_ids["smile"], "weight": 1.0}]
        builder._apply_scene_character_actions(10, actions, layers)

        assert layers[LAYER_EXPRESSION] == []  # not cleared, not injected

    def test_non_expression_action_layers_not_cleared(self, db_session):
        """Tags targeting other layers (e.g. LAYER_ENVIRONMENT) should append, not clear."""
        tag_ids = self._seed_tags(db_session, [("night", LAYER_ENVIRONMENT)])
        builder = PromptBuilder(db_session)

        layers = [[] for _ in range(12)]
        layers[LAYER_ENVIRONMENT] = ["park", "outdoors"]

        actions = [{"character_id": 1, "tag_id": tag_ids["night"], "weight": 1.0}]
        builder._apply_scene_character_actions(1, actions, layers)

        # LAYER_ENVIRONMENT should be appended to, not cleared
        assert "park" in layers[LAYER_ENVIRONMENT]
        assert "outdoors" in layers[LAYER_ENVIRONMENT]
        assert "night" in layers[LAYER_ENVIRONMENT]

    def test_unknown_tag_id_skipped(self, db_session):
        """Actions with tag_id not in DB should be silently skipped."""
        builder = PromptBuilder(db_session)

        layers = [[] for _ in range(12)]
        layers[LAYER_EXPRESSION] = ["smile"]

        actions = [{"character_id": 1, "tag_id": 99999, "weight": 1.0}]
        builder._apply_scene_character_actions(1, actions, layers)

        # Expression layer NOT cleared because no valid actions resolved
        assert layers[LAYER_EXPRESSION] == ["smile"]

    def test_empty_actions_noop(self, db_session):
        """Empty actions list should not modify layers."""
        builder = PromptBuilder(db_session)

        layers = [[] for _ in range(12)]
        layers[LAYER_EXPRESSION] = ["smile"]

        builder._apply_scene_character_actions(1, [], layers)

        assert layers[LAYER_EXPRESSION] == ["smile"]

    def test_compose_for_character_integrates_actions(self, db_session):
        """End-to-end: compose_for_character with scene_character_actions."""
        from models.character import Character

        tag_ids = self._seed_tags(db_session, [("crying", LAYER_EXPRESSION), ("kneeling", LAYER_ACTION)])
        char = Character(name="test_char", positive_prompt="1girl", group_id=1)
        db_session.add(char)
        db_session.flush()

        actions = [
            {"character_id": char.id, "tag_id": tag_ids["crying"], "weight": 1.0},
            {"character_id": char.id, "tag_id": tag_ids["kneeling"], "weight": 1.0},
        ]

        builder = PromptBuilder(db_session)
        result = builder.compose_for_character(
            char.id,
            scene_tags=["1girl", "park"],
            scene_character_actions=actions,
            character=char,
        )

        # Scene actions should appear in output (with :1.2 boost from _flatten_layers)
        assert "(crying:1.2)" in result
        assert "(kneeling:1.2)" in result


# ────────────────────────────────────────────
# Realistic Style Profile quality tag tests
# ────────────────────────────────────────────


class TestEnsureQualityTagsRealistic:
    """_ensure_quality_tags should respect existing quality tags (no anime fallback)."""

    def test_empty_quality_layer_gets_fallback(self):
        """Empty LAYER_QUALITY → fallback tags injected."""
        layers = [[] for _ in range(12)]
        PromptBuilder._ensure_quality_tags(layers)

        quality = layers[LAYER_QUALITY]
        assert "masterpiece" in quality
        assert "best_quality" in quality

    def test_realistic_quality_tags_preserved(self):
        """Realistic tags in LAYER_QUALITY → no anime fallback injected."""
        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["photorealistic", "raw_photo", "sharp_focus"]

        PromptBuilder._ensure_quality_tags(layers)

        quality = layers[LAYER_QUALITY]
        assert "photorealistic" in quality
        assert "raw_photo" in quality
        assert "masterpiece" not in quality
        assert "best_quality" not in quality

    def test_anime_quality_tags_preserved(self):
        """Anime tags already in LAYER_QUALITY → no duplicate injection."""
        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["masterpiece", "best_quality"]

        PromptBuilder._ensure_quality_tags(layers)

        quality = layers[LAYER_QUALITY]
        assert quality.count("masterpiece") == 1
        assert quality.count("best_quality") == 1

    def test_mixed_quality_tags_not_overridden(self):
        """Any non-empty LAYER_QUALITY → skip fallback entirely."""
        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["high_resolution"]

        PromptBuilder._ensure_quality_tags(layers)

        quality = layers[LAYER_QUALITY]
        assert "high_resolution" in quality
        assert "masterpiece" not in quality


class TestInferLayerQualityKeywords:
    """_infer_layer_from_pattern should classify realistic quality tags to LAYER_QUALITY."""

    def test_photorealistic_is_style_not_quality(self):
        # photorealistic belongs to CATEGORY_PATTERNS["style"] → LAYER_ATMOSPHERE
        assert PromptBuilder._infer_layer_from_pattern("photorealistic") == LAYER_ATMOSPHERE

    def test_raw_photo(self):
        assert PromptBuilder._infer_layer_from_pattern("raw_photo") == LAYER_QUALITY

    def test_sharp_focus(self):
        assert PromptBuilder._infer_layer_from_pattern("sharp_focus") == LAYER_QUALITY

    def test_film_grain(self):
        assert PromptBuilder._infer_layer_from_pattern("film_grain") == LAYER_QUALITY

    def test_8k_uhd(self):
        assert PromptBuilder._infer_layer_from_pattern("8k_uhd") == LAYER_QUALITY

    def test_dslr(self):
        assert PromptBuilder._infer_layer_from_pattern("dslr") == LAYER_QUALITY

    def test_masterpiece_still_quality(self):
        """Existing anime quality tags should also classify as LAYER_QUALITY."""
        assert PromptBuilder._infer_layer_from_pattern("masterpiece") == LAYER_QUALITY

    def test_best_quality(self):
        assert PromptBuilder._infer_layer_from_pattern("best_quality") == LAYER_QUALITY

    def test_highres(self):
        assert PromptBuilder._infer_layer_from_pattern("highres") == LAYER_QUALITY

    def test_absurdres(self):
        assert PromptBuilder._infer_layer_from_pattern("absurdres") == LAYER_QUALITY


# ────────────────────────────────────────────
# compose_for_reference quality_tags tests
# ────────────────────────────────────────────


class TestComposeForReferenceQuality:
    """compose_for_reference should accept quality_tags to avoid anime fallback."""

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_default_quality_fallback(self, mock_alias, mock_filter, mock_rule, builder):
        """No quality_tags → fallback quality tags."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        char = MagicMock()
        char.gender = "female"
        char.tags = []
        char.loras = []
        char.positive_prompt = "1girl"
        char.positive_prompt = None

        result = builder.compose_for_reference(char)

        assert "masterpiece" in result
        assert "best_quality" in result

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_realistic_quality_tags_override(self, mock_alias, mock_filter, mock_rule, builder):
        """Explicit quality_tags → no anime fallback."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        char = MagicMock()
        char.gender = "female"
        char.tags = []
        char.loras = []
        char.positive_prompt = "1girl"
        char.positive_prompt = None

        result = builder.compose_for_reference(char, quality_tags=["photorealistic", "raw_photo"])

        assert "photorealistic" in result
        assert "raw_photo" in result
        assert "masterpiece" not in result
        assert "best_quality" not in result


class TestLoRABaseModelCompatibility:
    """Test LoRA base_model compatibility warning in _inject_loras."""

    @patch("services.prompt.composition.LoRATriggerCache")
    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_mismatch_produces_warning(self, mock_alias, mock_filter, mock_rule, mock_trigger):
        """LoRA base_model != checkpoint base → warning added."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False
        mock_trigger.get_lora_name.return_value = None

        mock_db = MagicMock()

        # LoRA with SDXL base_model
        mock_lora = MagicMock()
        mock_lora.name = "anime_char_lora"
        mock_lora.lora_type = "character"
        mock_lora.base_model = "SDXL"
        mock_lora.trigger_words = []
        mock_lora.default_weight = 0.7
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lora

        char = MagicMock()
        char.loras = [{"lora_id": 1, "weight": 0.8}]

        builder = PromptBuilder(mock_db, sd_model_base="SD1.5")
        layers = [[] for _ in range(12)]
        builder._inject_loras(char, [], layers, [])

        assert len(builder.warnings) == 1
        assert "incompatible" in builder.warnings[0]
        assert "SDXL" in builder.warnings[0]
        assert "SD1.5" in builder.warnings[0]

    @patch("services.prompt.composition.LoRATriggerCache")
    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_null_base_model_no_warning(self, mock_alias, mock_filter, mock_rule, mock_trigger):
        """LoRA without base_model (NULL) → no warning (gradual adoption)."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False
        mock_trigger.get_lora_name.return_value = None

        mock_db = MagicMock()

        mock_lora = MagicMock()
        mock_lora.name = "old_lora"
        mock_lora.lora_type = "character"
        mock_lora.base_model = None  # Not set yet
        mock_lora.trigger_words = []
        mock_lora.default_weight = 0.7
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lora

        char = MagicMock()
        char.loras = [{"lora_id": 1, "weight": 0.8}]

        builder = PromptBuilder(mock_db, sd_model_base="SD1.5")
        layers = [[] for _ in range(12)]
        builder._inject_loras(char, [], layers, [])

        assert len(builder.warnings) == 0

    @patch("services.prompt.composition.LoRATriggerCache")
    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_matching_base_model_no_warning(self, mock_alias, mock_filter, mock_rule, mock_trigger):
        """LoRA base_model == checkpoint base → no warning."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False
        mock_trigger.get_lora_name.return_value = None

        mock_db = MagicMock()

        mock_lora = MagicMock()
        mock_lora.name = "sd15_char"
        mock_lora.lora_type = "character"
        mock_lora.base_model = "SD1.5"
        mock_lora.trigger_words = ["sd15_trigger"]
        mock_lora.default_weight = 0.7
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lora

        char = MagicMock()
        char.loras = [{"lora_id": 1, "weight": 0.8}]

        builder = PromptBuilder(mock_db, sd_model_base="SD1.5")
        layers = [[] for _ in range(12)]
        builder._inject_loras(char, [], layers, [])

        assert len(builder.warnings) == 0


# ────────────────────────────────────────────
# Layer capture tests (Phase 15-A-0-1)
# ────────────────────────────────────────────


class TestLayerCapture:
    """Tests for _last_composed_layers capture and get_last_composed_layers accessor."""

    def test_layer_names_count(self):
        """LAYER_NAMES should have exactly 12 entries."""
        assert len(LAYER_NAMES) == 12

    @patch("services.prompt.composition.TagRuleCache")
    def test_flatten_stores_composed_layers(self, mock_cache, builder):
        """_flatten_layers should populate _last_composed_layers."""
        mock_cache.initialize.return_value = None
        mock_cache.is_conflicting.return_value = False

        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["masterpiece", "best_quality"]
        layers[LAYER_IDENTITY] = ["brown_hair"]

        builder._flatten_layers(layers)

        assert builder._last_composed_layers is not None
        assert len(builder._last_composed_layers) == 12
        assert builder._last_composed_layers[LAYER_QUALITY] == ["masterpiece", "best_quality"]
        assert builder._last_composed_layers[LAYER_IDENTITY] == ["brown_hair"]

    @patch("services.prompt.composition.TagRuleCache")
    def test_get_last_composed_layers_format(self, mock_cache, builder):
        """Accessor should return list of {index, name, tokens}, excluding empty layers."""
        mock_cache.initialize.return_value = None
        mock_cache.is_conflicting.return_value = False

        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["masterpiece"]
        layers[LAYER_CAMERA] = ["cowboy_shot"]

        builder._flatten_layers(layers)
        result = builder.get_last_composed_layers()

        assert result is not None
        assert len(result) == 2  # Only non-empty layers
        assert result[0] == {"index": 0, "name": "Quality", "tokens": ["masterpiece"]}
        assert result[1] == {"index": 9, "name": "Camera", "tokens": ["cowboy_shot"]}

    def test_get_last_composed_layers_none_before_compose(self, builder):
        """Accessor should return None before any compose call."""
        assert builder.get_last_composed_layers() is None

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_compose_populates_layers(self, mock_alias, mock_rule, builder):
        """compose() should populate _last_composed_layers via _flatten_layers."""
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...  # No alias

        builder.get_tag_info = MagicMock(
            return_value={"brown_hair": {"layer": LAYER_IDENTITY, "scope": "ANY", "group_name": None}}
        )

        builder.compose(["brown_hair"])
        result = builder.get_last_composed_layers()

        assert result is not None
        layer_names = [l["name"] for l in result]
        assert "Identity" in layer_names

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagAliasCache")
    @patch("services.prompt.composition.TagFilterCache")
    def test_compose_for_character_populates_layers(self, mock_filter, mock_alias, mock_rule, builder):
        """compose_for_character() should also populate layers."""
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False

        char = MagicMock()
        char.id = 1
        char.gender = "female"
        char.positive_prompt = "brown_hair"
        char.tags = []
        char.loras = []

        builder.db.query.return_value.filter.return_value.first.return_value = char

        builder.get_tag_info = MagicMock(return_value={})

        builder.compose_for_character(character_id=1, scene_tags=["smile"])
        result = builder.get_last_composed_layers()

        assert result is not None
        assert len(result) > 0

    @patch("services.prompt.composition.TagRuleCache")
    def test_layer_dedup_in_composed_layers(self, mock_cache, builder):
        """Duplicate tags should only appear in the first layer they're placed in."""
        mock_cache.initialize.return_value = None
        mock_cache.is_conflicting.return_value = False

        layers = [[] for _ in range(12)]
        layers[LAYER_QUALITY] = ["masterpiece"]
        layers[LAYER_IDENTITY] = ["brown_hair"]
        layers[LAYER_ENVIRONMENT] = ["masterpiece", "classroom"]  # dup masterpiece

        builder._flatten_layers(layers)
        result = builder.get_last_composed_layers()

        quality_layer = next(l for l in result if l["name"] == "Quality")
        env_layer = next(l for l in result if l["name"] == "Environment")
        assert "masterpiece" in quality_layer["tokens"]
        assert "masterpiece" not in env_layer["tokens"]


# ────────────────────────────────────────────
# LoRAInfo + trigger word injection tests
# ────────────────────────────────────────────


class TestLoRAInfo:
    """LoRAInfo 데이터 클래스 테스트."""

    def test_lora_info_attributes(self):
        from services.prompt.composition import LoRAInfo

        info = LoRAInfo(0.8, "style", ["flat color", "anime_style"])
        assert info.weight == 0.8
        assert info.lora_type == "style"
        assert info.trigger_words == ["flat color", "anime_style"]

    def test_lora_info_no_triggers(self):
        from services.prompt.composition import LoRAInfo

        info = LoRAInfo(0.7, None, [])
        assert info.trigger_words == []

    def test_get_lora_info_returns_lora_info(self, builder):
        """_get_lora_info가 LoRAInfo 객체를 반환하는지 확인."""
        from services.prompt.composition import LoRAInfo

        info = builder._get_lora_info("nonexistent_lora")
        assert isinstance(info, LoRAInfo)
        assert info.weight == 0.7
        assert info.lora_type is None
        assert info.trigger_words == []

    def test_get_lora_info_with_db_lora(self):
        """DB에 LoRA가 있을 때 trigger_words 포함 반환."""
        from services.prompt.composition import LoRAInfo

        mock_db = MagicMock()
        mock_lora = MagicMock()
        mock_lora.default_weight = 0.7
        mock_lora.lora_type = "style"
        mock_lora.trigger_words = ["flat color"]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lora

        builder = PromptBuilder(mock_db)
        info = builder._get_lora_info("test_lora")
        assert isinstance(info, LoRAInfo)
        assert info.weight == 0.7
        assert info.lora_type == "style"
        assert info.trigger_words == ["flat color"]

    def test_get_lora_weight_by_name(self, builder):
        """get_lora_weight_by_name이 LoRAInfo.weight를 반환."""
        weight = builder.get_lora_weight_by_name("nonexistent")
        assert weight == 0.7


# ────────────────────────────────────────────
# Pattern-based fallback: GROUP_NAME_TO_LAYER SSOT
# ────────────────────────────────────────────


class TestPatternBasedFallbackExtended:
    """_infer_layer_from_pattern should resolve all 26 CATEGORY_PATTERNS groups."""

    # clothing → LAYER_MAIN_CLOTH (4)
    def test_hoodie_is_main_cloth(self):
        assert PromptBuilder._infer_layer_from_pattern("hoodie") == LAYER_MAIN_CLOTH

    def test_school_uniform_is_main_cloth(self):
        assert PromptBuilder._infer_layer_from_pattern("school_uniform") == LAYER_MAIN_CLOTH

    def test_striped_shirt_is_main_cloth(self):
        assert PromptBuilder._infer_layer_from_pattern("striped_shirt") == LAYER_MAIN_CLOTH

    def test_overalls_is_main_cloth(self):
        assert PromptBuilder._infer_layer_from_pattern("overalls") == LAYER_MAIN_CLOTH

    # gaze → LAYER_EXPRESSION (7)
    def test_looking_at_viewer_is_expression(self):
        assert PromptBuilder._infer_layer_from_pattern("looking_at_viewer") == LAYER_EXPRESSION

    def test_looking_away_is_expression(self):
        assert PromptBuilder._infer_layer_from_pattern("looking_away") == LAYER_EXPRESSION

    # pose → LAYER_ACTION (8)
    def test_standing_is_action(self):
        assert PromptBuilder._infer_layer_from_pattern("standing") == LAYER_ACTION

    def test_sitting_is_action(self):
        assert PromptBuilder._infer_layer_from_pattern("sitting") == LAYER_ACTION

    def test_arms_crossed_is_action(self):
        assert PromptBuilder._infer_layer_from_pattern("arms_crossed") == LAYER_ACTION

    # body_feature → LAYER_BODY (3)
    def test_pointy_ears_is_body(self):
        assert PromptBuilder._infer_layer_from_pattern("pointy_ears") == LAYER_BODY

    def test_wings_is_body(self):
        assert PromptBuilder._infer_layer_from_pattern("wings") == LAYER_BODY

    # appearance → LAYER_BODY (3)
    def test_freckles_is_body(self):
        assert PromptBuilder._infer_layer_from_pattern("freckles") == LAYER_BODY

    def test_muscular_is_body(self):
        assert PromptBuilder._infer_layer_from_pattern("muscular") == LAYER_BODY

    # camera → LAYER_CAMERA (9)
    def test_close_up_is_camera(self):
        assert PromptBuilder._infer_layer_from_pattern("close-up") == LAYER_CAMERA

    def test_upper_body_is_camera(self):
        assert PromptBuilder._infer_layer_from_pattern("upper_body") == LAYER_CAMERA

    def test_dutch_angle_is_camera(self):
        assert PromptBuilder._infer_layer_from_pattern("dutch_angle") == LAYER_CAMERA

    # lighting → LAYER_ATMOSPHERE (11)
    def test_backlighting_is_atmosphere(self):
        assert PromptBuilder._infer_layer_from_pattern("backlighting") == LAYER_ATMOSPHERE

    def test_dramatic_lighting_is_atmosphere(self):
        assert PromptBuilder._infer_layer_from_pattern("dramatic_lighting") == LAYER_ATMOSPHERE

    # style → LAYER_ATMOSPHERE (11)
    def test_watercolor_is_atmosphere(self):
        assert PromptBuilder._infer_layer_from_pattern("watercolor") == LAYER_ATMOSPHERE

    # time_weather → LAYER_ENVIRONMENT (10)
    def test_sunset_is_environment(self):
        assert PromptBuilder._infer_layer_from_pattern("sunset") == LAYER_ENVIRONMENT

    def test_cherry_blossoms_is_environment(self):
        assert PromptBuilder._infer_layer_from_pattern("cherry_blossoms") == LAYER_ENVIRONMENT

    # hair_accessory → LAYER_ACCESSORY (6)
    def test_hairclip_is_accessory(self):
        assert PromptBuilder._infer_layer_from_pattern("hairclip") == LAYER_ACCESSORY

    def test_tiara_is_accessory(self):
        assert PromptBuilder._infer_layer_from_pattern("tiara") == LAYER_ACCESSORY

    # novel suffix heuristic
    def test_novel_dress_suffix_is_main_cloth(self):
        assert PromptBuilder._infer_layer_from_pattern("magical_girl_dress") == LAYER_MAIN_CLOTH


# ────────────────────────────────────────────
# _tag_to_group_map tests
# ────────────────────────────────────────────


class TestTagToGroupMap:
    """Test _tag_to_group_map returns correct group_name for pattern tags."""

    def test_expression_tags(self):
        group_map = PromptBuilder._tag_to_group_map()
        assert group_map["smile"] == "expression"
        assert group_map["crying"] == "expression"
        assert group_map["angry"] == "expression"

    def test_gaze_tags(self):
        group_map = PromptBuilder._tag_to_group_map()
        assert group_map["looking_at_viewer"] == "gaze"
        assert group_map["looking_away"] == "gaze"

    def test_lighting_tags(self):
        group_map = PromptBuilder._tag_to_group_map()
        assert group_map["soft_lighting"] == "lighting"
        assert group_map["dramatic_lighting"] == "lighting"

    def test_clothing_tags(self):
        group_map = PromptBuilder._tag_to_group_map()
        assert group_map["hoodie"] == "clothing_top"
        assert group_map["school_uniform"] == "clothing_outfit"

    def test_quality_tags(self):
        group_map = PromptBuilder._tag_to_group_map()
        assert group_map["masterpiece"] == "quality"

    def test_unknown_tag_not_in_map(self):
        group_map = PromptBuilder._tag_to_group_map()
        assert "unknown_fantasy_tag" not in group_map


# ────────────────────────────────────────────
# get_tag_info group_name pattern fallback
# ────────────────────────────────────────────


class TestGetTagInfoGroupNameFallback:
    """Test get_tag_info returns group_name from pattern fallback for DB-missing tags."""

    def test_pattern_fallback_includes_group_name(self, builder):
        """DB-missing tag should still get group_name from CATEGORY_PATTERNS."""
        # Mock DB query to return no tags
        builder.db.query.return_value.filter.return_value.all.return_value = []

        result = builder.get_tag_info(["gentle_smile"])
        # gentle_smile is not in CATEGORY_PATTERNS, so group_name=None
        assert result["gentle_smile"]["group_name"] is None

    def test_known_pattern_tag_gets_group(self, builder):
        """Tag in CATEGORY_PATTERNS should get correct group_name even without DB."""
        builder.db.query.return_value.filter.return_value.all.return_value = []

        result = builder.get_tag_info(["crying"])
        assert result["crying"]["group_name"] == "expression"
        assert result["crying"]["layer"] == LAYER_EXPRESSION

    def test_lighting_pattern_tag_gets_group(self, builder):
        builder.db.query.return_value.filter.return_value.all.return_value = []

        result = builder.get_tag_info(["soft_lighting"])
        assert result["soft_lighting"]["group_name"] == "lighting"
        assert result["soft_lighting"]["layer"] == LAYER_ATMOSPHERE

    def test_clothing_pattern_tag_gets_group(self, builder):
        builder.db.query.return_value.filter.return_value.all.return_value = []

        result = builder.get_tag_info(["hoodie"])
        assert result["hoodie"]["group_name"] == "clothing_top"
        assert result["hoodie"]["layer"] == LAYER_MAIN_CLOTH


# ────────────────────────────────────────────
# _collect_character_tags layer placement
# ────────────────────────────────────────────


class TestCollectCharacterTagsLayerPlacement:
    """Test positive_prompt tags get correct layer/group_name from DB or pattern."""

    @patch("services.prompt.composition.TagFilterCache")
    def test_expression_tag_placed_in_expression_layer(self, mock_filter, builder):
        """gentle_smile from positive_prompt → layer from DB (LAYER_EXPRESSION)."""
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False

        from models.tag import Tag

        mock_tag = MagicMock(spec=Tag)
        mock_tag.name = "gentle_smile"
        mock_tag.default_layer = LAYER_EXPRESSION
        mock_tag.usage_scope = "ANY"
        mock_tag.group_name = "expression"

        builder.db.query.return_value.filter.return_value.all.return_value = [mock_tag]

        char = MagicMock()
        char.tags = []
        char.positive_prompt = "gentle_smile"

        result = builder._collect_character_tags(char)
        tag_data = next(t for t in result if t["name"] == "gentle_smile")
        assert tag_data["layer"] == LAYER_EXPRESSION
        assert tag_data["group_name"] == "expression"

    @patch("services.prompt.composition.TagFilterCache")
    def test_lighting_tag_placed_in_atmosphere_layer(self, mock_filter, builder):
        """soft_lighting → LAYER_ATMOSPHERE."""
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False

        from models.tag import Tag

        mock_tag = MagicMock(spec=Tag)
        mock_tag.name = "soft_lighting"
        mock_tag.default_layer = LAYER_ATMOSPHERE
        mock_tag.usage_scope = "ANY"
        mock_tag.group_name = "lighting"

        builder.db.query.return_value.filter.return_value.all.return_value = [mock_tag]

        char = MagicMock()
        char.tags = []
        char.positive_prompt = "soft_lighting"

        result = builder._collect_character_tags(char)
        tag_data = next(t for t in result if t["name"] == "soft_lighting")
        assert tag_data["layer"] == LAYER_ATMOSPHERE
        assert tag_data["group_name"] == "lighting"

    @patch("services.prompt.composition.TagFilterCache")
    def test_clothing_tag_placed_in_main_cloth_layer(self, mock_filter, builder):
        """blouse → LAYER_MAIN_CLOTH via pattern fallback."""
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False

        # No DB match — pattern fallback via CATEGORY_PATTERNS
        builder.db.query.return_value.filter.return_value.all.return_value = []

        char = MagicMock()
        char.tags = []
        char.positive_prompt = "blouse"

        result = builder._collect_character_tags(char)
        tag_data = next(t for t in result if t["name"] == "blouse")
        assert tag_data["layer"] == LAYER_MAIN_CLOTH
        assert tag_data["group_name"] == "clothing_top"

    @patch("services.prompt.composition.TagFilterCache")
    def test_quality_tag_placed_in_quality_layer(self, mock_filter, builder):
        """masterpiece → LAYER_QUALITY."""
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False

        builder.db.query.return_value.filter.return_value.all.return_value = []

        char = MagicMock()
        char.tags = []
        char.positive_prompt = "masterpiece"

        result = builder._collect_character_tags(char)
        tag_data = next(t for t in result if t["name"] == "masterpiece")
        assert tag_data["layer"] == LAYER_QUALITY

    @patch("services.prompt.composition.TagFilterCache")
    def test_multiple_tags_correct_layers(self, mock_filter, builder):
        """Multiple positive_prompt tags → each gets correct layer."""
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False

        from models.tag import Tag

        gentle = MagicMock(spec=Tag)
        gentle.name = "gentle_smile"
        gentle.default_layer = LAYER_EXPRESSION
        gentle.usage_scope = "ANY"
        gentle.group_name = "expression"

        soft = MagicMock(spec=Tag)
        soft.name = "soft_lighting"
        soft.default_layer = LAYER_ATMOSPHERE
        soft.usage_scope = "ANY"
        soft.group_name = "lighting"

        builder.db.query.return_value.filter.return_value.all.return_value = [gentle, soft]

        char = MagicMock()
        char.tags = []
        char.positive_prompt = "gentle_smile, soft_lighting, hoodie"

        result = builder._collect_character_tags(char)
        layers = {t["name"]: t["layer"] for t in result}

        assert layers["gentle_smile"] == LAYER_EXPRESSION
        assert layers["soft_lighting"] == LAYER_ATMOSPHERE
        assert layers["hoodie"] == LAYER_MAIN_CLOTH  # pattern fallback


# ────────────────────────────────────────────
# Dynamic scene override tests (group-based, no hardcoded list)
# ────────────────────────────────────────────


class TestSceneOverrideGroups:
    """Test scene tags dynamically override character base defaults.

    Rule: scene groups NOT in EXCLUSIVE_TAG_GROUPS suppress matching char base tags.
    """

    def test_scene_crying_overrides_char_gentle_smile(self, builder):
        """Scene crying → char gentle_smile excluded."""
        char_info = {
            "gentle_smile": _make_tag_info("gentle_smile", LAYER_EXPRESSION, group="expression"),
            "brown_hair": _make_tag_info("brown_hair", LAYER_IDENTITY, group="hair_color"),
        }
        scene_info = {
            "crying": _make_tag_info("crying", LAYER_EXPRESSION, group="expression"),
            "outdoors": _make_tag_info("outdoors", LAYER_ENVIRONMENT, group="location_outdoor"),
        }
        all_info = {**char_info, **scene_info}
        builder.get_tag_info = MagicMock(
            side_effect=lambda names: {
                n: all_info[n] for n in [t.lower().replace(" ", "_").strip() for t in names] if n in all_info
            }
        )

        char_tags = [
            {"name": "gentle_smile", "layer": LAYER_EXPRESSION, "weight": 1.0, "group_name": "expression"},
            {"name": "brown_hair", "layer": LAYER_IDENTITY, "weight": 1.0, "group_name": "hair_color"},
        ]
        scene_tags = ["crying", "outdoors"]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, scene_tags, scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "crying" in all_tokens
        assert "gentle_smile" not in all_tokens
        assert "brown_hair" in all_tokens
        assert "outdoors" in all_tokens

    def test_scene_gaze_overrides_char_gaze(self, builder):
        """Scene looking_away → char looking_at_viewer excluded."""
        char_info = {"looking_at_viewer": _make_tag_info("looking_at_viewer", LAYER_EXPRESSION, group="gaze")}
        scene_info = {"looking_away": _make_tag_info("looking_away", LAYER_EXPRESSION, group="gaze")}
        all_info = {**char_info, **scene_info}
        builder.get_tag_info = MagicMock(
            side_effect=lambda names: {
                n: all_info[n] for n in [t.lower().replace(" ", "_").strip() for t in names] if n in all_info
            }
        )

        char_tags = [
            {"name": "looking_at_viewer", "layer": LAYER_EXPRESSION, "weight": 1.0, "group_name": "gaze"},
        ]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["looking_away"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "looking_away" in all_tokens
        assert "looking_at_viewer" not in all_tokens

    def test_no_scene_expression_keeps_char_default(self, builder):
        """No scene expression → char gentle_smile preserved."""
        scene_info = {
            "outdoors": _make_tag_info("outdoors", LAYER_ENVIRONMENT, group="location_outdoor"),
        }
        builder.get_tag_info = MagicMock(
            side_effect=lambda names: {
                n: scene_info[n] for n in [t.lower().replace(" ", "_").strip() for t in names] if n in scene_info
            }
        )

        char_tags = [
            {"name": "gentle_smile", "layer": LAYER_EXPRESSION, "weight": 1.0, "group_name": "expression"},
        ]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["outdoors"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "gentle_smile" in all_tokens
        assert "outdoors" in all_tokens

    def test_scene_dark_overrides_char_soft_lighting(self, builder):
        """Scene dark → char soft_lighting excluded (lighting override)."""
        char_info = {
            "soft_lighting": _make_tag_info("soft_lighting", LAYER_ATMOSPHERE, group="lighting"),
            "brown_hair": _make_tag_info("brown_hair", LAYER_IDENTITY, group="hair_color"),
        }
        scene_info = {
            "dark": _make_tag_info("dark", LAYER_ATMOSPHERE, group="lighting"),
            "indoors": _make_tag_info("indoors", LAYER_ENVIRONMENT, group="location_indoor"),
        }
        all_info = {**char_info, **scene_info}
        builder.get_tag_info = MagicMock(
            side_effect=lambda names: {
                n: all_info[n] for n in [t.lower().replace(" ", "_").strip() for t in names] if n in all_info
            }
        )

        char_tags = [
            {"name": "soft_lighting", "layer": LAYER_ATMOSPHERE, "weight": 1.0, "group_name": "lighting"},
            {"name": "brown_hair", "layer": LAYER_IDENTITY, "weight": 1.0, "group_name": "hair_color"},
        ]
        scene_tags = ["dark", "indoors"]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, scene_tags, scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "dark" in all_tokens
        assert "soft_lighting" not in all_tokens
        assert "brown_hair" in all_tokens  # identity preserved

    def test_identity_group_never_overridden(self, builder):
        """EXCLUSIVE_TAG_GROUPS (hair_color etc.) never overridden by scene."""
        char_info = {
            "brown_hair": _make_tag_info("brown_hair", LAYER_IDENTITY, group="hair_color"),
        }
        scene_info = {
            "blonde_hair": _make_tag_info("blonde_hair", LAYER_IDENTITY, group="hair_color"),
        }
        all_info = {**char_info, **scene_info}
        builder.get_tag_info = MagicMock(
            side_effect=lambda names: {
                n: all_info[n] for n in [t.lower().replace(" ", "_").strip() for t in names] if n in all_info
            }
        )

        char_tags = [
            {"name": "brown_hair", "layer": LAYER_IDENTITY, "weight": 1.0, "group_name": "hair_color"},
        ]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["blonde_hair"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "brown_hair" in all_tokens  # identity group protected

    def test_clothing_group_protected_by_exclusive(self, builder):
        """Clothing group in EXCLUSIVE_TAG_GROUPS: scene clothing tags cannot override char clothing."""
        char_info = {
            "school_uniform": _make_tag_info("school_uniform", LAYER_MAIN_CLOTH, group="clothing"),
        }
        scene_info = {
            "casual_clothes": _make_tag_info("casual_clothes", LAYER_MAIN_CLOTH, group="clothing"),
        }
        all_info = {**char_info, **scene_info}
        builder.get_tag_info = MagicMock(
            side_effect=lambda names: {
                n: all_info[n] for n in [t.lower().replace(" ", "_").strip() for t in names] if n in all_info
            }
        )

        char_tags = [
            {"name": "school_uniform", "layer": LAYER_MAIN_CLOTH, "weight": 1.0, "group_name": "clothing"},
        ]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["casual_clothes"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "school_uniform" in all_tokens  # char clothing protected
        assert "casual_clothes" not in all_tokens  # scene clothing blocked

    def test_accessory_group_protected_by_exclusive(self, builder):
        """Accessory group in EXCLUSIVE_TAG_GROUPS: scene accessory tags cannot override char accessory."""
        char_info = {
            "glasses": _make_tag_info("glasses", LAYER_ACCESSORY, group="accessory"),
        }
        scene_info = {
            "hat": _make_tag_info("hat", LAYER_ACCESSORY, group="accessory"),
        }
        all_info = {**char_info, **scene_info}
        builder.get_tag_info = MagicMock(
            side_effect=lambda names: {
                n: all_info[n] for n in [t.lower().replace(" ", "_").strip() for t in names] if n in all_info
            }
        )

        char_tags = [
            {"name": "glasses", "layer": LAYER_ACCESSORY, "weight": 1.0, "group_name": "accessory"},
        ]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["hat"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "glasses" in all_tokens  # char accessory protected
        assert "hat" not in all_tokens  # scene accessory blocked

    def test_non_override_group_not_affected(self, builder):
        """Clothing group not overridden when scene has different groups."""
        scene_info = {
            "crying": _make_tag_info("crying", LAYER_EXPRESSION, group="expression"),
        }
        builder.get_tag_info = MagicMock(
            side_effect=lambda names: {
                n: scene_info[n] for n in [t.lower().replace(" ", "_").strip() for t in names] if n in scene_info
            }
        )

        char_tags = [
            {"name": "hoodie", "layer": LAYER_MAIN_CLOTH, "weight": 1.0, "group_name": "clothing"},
            {"name": "gentle_smile", "layer": LAYER_EXPRESSION, "weight": 1.0, "group_name": "expression"},
        ]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["crying"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "hoodie" in all_tokens  # clothing not overridden
        assert "gentle_smile" not in all_tokens  # expression overridden
        assert "crying" in all_tokens

    def test_char_tags_without_group_name_not_affected(self, builder):
        """Char tags with group_name=None not affected by scene override."""
        scene_info = {
            "crying": _make_tag_info("crying", LAYER_EXPRESSION, group="expression"),
        }
        builder.get_tag_info = MagicMock(
            side_effect=lambda names: {
                n: scene_info[n] for n in [t.lower().replace(" ", "_").strip() for t in names] if n in scene_info
            }
        )

        char_tags = [
            {"name": "1girl", "layer": LAYER_SUBJECT, "weight": 1.0, "group_name": None},
        ]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["crying"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "1girl" in all_tokens


# ────────────────────────────────────────────
# End-to-end expression override tests
# ────────────────────────────────────────────


class TestEndToEndExpressionOverride:
    """Full pipeline test: compose_for_character with expression override."""

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_scene_expression_overrides_in_full_pipeline(self, mock_alias, mock_filter, mock_rule, builder):
        """compose_for_character: scene crying should suppress char gentle_smile."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        from models.tag import Tag

        # DB returns gentle_smile with correct metadata
        gentle_tag = MagicMock(spec=Tag)
        gentle_tag.name = "gentle_smile"
        gentle_tag.default_layer = LAYER_EXPRESSION
        gentle_tag.usage_scope = "ANY"
        gentle_tag.group_name = "expression"

        crying_tag = MagicMock(spec=Tag)
        crying_tag.name = "crying"
        crying_tag.default_layer = LAYER_EXPRESSION
        crying_tag.usage_scope = "ANY"
        crying_tag.group_name = "expression"

        outdoors_tag = MagicMock(spec=Tag)
        outdoors_tag.name = "outdoors"
        outdoors_tag.default_layer = LAYER_ENVIRONMENT
        outdoors_tag.usage_scope = "ANY"
        outdoors_tag.group_name = "location_outdoor"

        all_tags = [gentle_tag, crying_tag, outdoors_tag]
        builder.db.query.return_value.filter.return_value.all.return_value = all_tags

        char = MagicMock()
        char.id = 1
        char.gender = "female"
        char.positive_prompt = "gentle_smile"
        char.tags = []
        char.loras = []

        builder.db.query.return_value.filter.return_value.first.return_value = char

        result = builder.compose_for_character(
            character_id=1,
            scene_tags=["crying", "outdoors"],
        )

        # crying should be present (with :1.2 boost from flatten)
        assert "(crying:1.2)" in result
        # gentle_smile should be suppressed
        assert "gentle_smile" not in result
        assert "outdoors" in result

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_no_scene_expression_keeps_char_default_full_pipeline(self, mock_alias, mock_filter, mock_rule, builder):
        """compose_for_character: no scene expression → char gentle_smile kept."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        from models.tag import Tag

        gentle_tag = MagicMock(spec=Tag)
        gentle_tag.name = "gentle_smile"
        gentle_tag.default_layer = LAYER_EXPRESSION
        gentle_tag.usage_scope = "ANY"
        gentle_tag.group_name = "expression"

        outdoors_tag = MagicMock(spec=Tag)
        outdoors_tag.name = "outdoors"
        outdoors_tag.default_layer = LAYER_ENVIRONMENT
        outdoors_tag.usage_scope = "ANY"
        outdoors_tag.group_name = "location_outdoor"

        all_tags = [gentle_tag, outdoors_tag]
        builder.db.query.return_value.filter.return_value.all.return_value = all_tags

        char = MagicMock()
        char.id = 1
        char.gender = "female"
        char.positive_prompt = "gentle_smile"
        char.tags = []
        char.loras = []

        builder.db.query.return_value.filter.return_value.first.return_value = char

        result = builder.compose_for_character(
            character_id=1,
            scene_tags=["outdoors"],
        )

        # gentle_smile should be present (with :1.2 boost from flatten)
        assert "(gentle_smile:1.2)" in result
        assert "outdoors" in result


# ────────────────────────────────────────────
# Weight syntax handling in get_tag_info / override
# ────────────────────────────────────────────


class TestWeightSyntaxHandling:
    """Verify get_tag_info and override logic handle SD weight tokens like (tag:1.1)."""

    def test_strip_weight_basic(self):
        """_strip_weight removes (tag:1.2) → tag."""
        assert PromptBuilder._strip_weight("(crying:1.1)") == "crying"
        assert PromptBuilder._strip_weight("(gentle_smile:1.15)") == "gentle_smile"

    def test_strip_weight_bare(self):
        """_strip_weight passes through bare tags."""
        assert PromptBuilder._strip_weight("crying") == "crying"
        assert PromptBuilder._strip_weight("brown_hair") == "brown_hair"

    def test_strip_weight_edge_cases(self):
        """_strip_weight handles edge cases."""
        assert PromptBuilder._strip_weight("(tag:0.5)") == "tag"
        assert PromptBuilder._strip_weight("not_weighted") == "not_weighted"
        # Parentheses without colon (not weight syntax)
        assert PromptBuilder._strip_weight("(test)") == "(test)"

    def test_get_tag_info_weighted_token(self, builder):
        """get_tag_info resolves (crying:1.1) to crying's DB metadata."""
        from models.tag import Tag

        crying_tag = MagicMock(spec=Tag)
        crying_tag.name = "crying"
        crying_tag.default_layer = LAYER_EXPRESSION
        crying_tag.usage_scope = "ANY"
        crying_tag.group_name = "expression"
        builder.db.query.return_value.filter.return_value.all.return_value = [crying_tag]

        result = builder.get_tag_info(["(crying:1.1)"])

        # Keyed by normalized weighted form
        assert "(crying:1.1)" in result
        assert result["(crying:1.1)"]["group_name"] == "expression"
        assert result["(crying:1.1)"]["layer"] == LAYER_EXPRESSION
        # Also keyed by bare form
        assert "crying" in result

    def test_get_tag_info_mixed_weighted_bare(self, builder):
        """get_tag_info handles mix of weighted and bare tokens."""
        from models.tag import Tag

        crying_tag = MagicMock(spec=Tag)
        crying_tag.name = "crying"
        crying_tag.default_layer = LAYER_EXPRESSION
        crying_tag.usage_scope = "ANY"
        crying_tag.group_name = "expression"

        outdoors_tag = MagicMock(spec=Tag)
        outdoors_tag.name = "outdoors"
        outdoors_tag.default_layer = LAYER_ENVIRONMENT
        outdoors_tag.usage_scope = "ANY"
        outdoors_tag.group_name = "location_outdoor"

        builder.db.query.return_value.filter.return_value.all.return_value = [crying_tag, outdoors_tag]

        result = builder.get_tag_info(["(crying:1.1)", "outdoors"])

        assert "(crying:1.1)" in result
        assert result["(crying:1.1)"]["group_name"] == "expression"
        assert "outdoors" in result
        assert result["outdoors"]["group_name"] == "location_outdoor"

    def test_scene_override_with_weighted_scene_tags(self, builder):
        """_distribute_tags: weighted scene (crying:1.1) overrides char expression."""
        scene_info = {
            "(crying:1.1)": _make_tag_info("crying", LAYER_EXPRESSION, group="expression"),
            "crying": _make_tag_info("crying", LAYER_EXPRESSION, group="expression"),
            "outdoors": _make_tag_info("outdoors", LAYER_ENVIRONMENT, group="location_outdoor"),
        }
        builder.get_tag_info = MagicMock(
            side_effect=lambda names: {
                n: scene_info[n] for n in [t.lower().replace(" ", "_").strip() for t in names] if n in scene_info
            }
        )

        char_tags = [
            {"name": "gentle_smile", "layer": LAYER_EXPRESSION, "weight": 1.0, "group_name": "expression"},
            {"name": "brown_hair", "layer": LAYER_IDENTITY, "weight": 1.0, "group_name": "hair_color"},
        ]
        layers = [[] for _ in range(12)]

        builder._distribute_tags(char_tags, ["(crying:1.1)", "outdoors"], scene_info, layers)

        all_tokens = [t for layer in layers for t in layer]
        assert "(crying:1.1)" in all_tokens
        assert "gentle_smile" not in all_tokens
        assert "brown_hair" in all_tokens

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_e2e_weighted_scene_expression_override(self, mock_alias, mock_filter, mock_rule, builder):
        """Full pipeline: weighted (crying:1.1) in scene → gentle_smile suppressed."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        from models.tag import Tag

        gentle_tag = MagicMock(spec=Tag)
        gentle_tag.name = "gentle_smile"
        gentle_tag.default_layer = LAYER_EXPRESSION
        gentle_tag.usage_scope = "ANY"
        gentle_tag.group_name = "expression"

        crying_tag = MagicMock(spec=Tag)
        crying_tag.name = "crying"
        crying_tag.default_layer = LAYER_EXPRESSION
        crying_tag.usage_scope = "ANY"
        crying_tag.group_name = "expression"

        outdoors_tag = MagicMock(spec=Tag)
        outdoors_tag.name = "outdoors"
        outdoors_tag.default_layer = LAYER_ENVIRONMENT
        outdoors_tag.usage_scope = "ANY"
        outdoors_tag.group_name = "location_outdoor"

        all_tags = [gentle_tag, crying_tag, outdoors_tag]
        builder.db.query.return_value.filter.return_value.all.return_value = all_tags

        char = MagicMock()
        char.id = 1
        char.gender = "female"
        char.positive_prompt = "gentle_smile"
        char.tags = []
        char.loras = []

        builder.db.query.return_value.filter.return_value.first.return_value = char

        result = builder.compose_for_character(
            character_id=1,
            scene_tags=["(crying:1.1)", "outdoors"],
        )

        # crying should be present (scene tag preserved as-is with weight)
        assert "(crying:1.1)" in result
        # gentle_smile should be suppressed
        assert "gentle_smile" not in result
        assert "outdoors" in result


# ────────────────────────────────────────────
# Strip character base tokens from scene dedup
# ────────────────────────────────────────────


class TestStripCharBaseFromScene:
    """Verify character base tokens are stripped from scene_tags to prevent duplication."""

    def test_strips_base_tokens(self):
        """positive_prompt tokens are removed from scene_tags."""
        char = MagicMock()
        char.positive_prompt = "gentle_smile, soft_lighting, masterpiece"

        scene_tags = ["crying", "gentle_smile", "soft_lighting", "outdoors", "masterpiece"]
        result = PromptBuilder._strip_char_base_from_scene(char, scene_tags)

        assert "crying" in result
        assert "outdoors" in result
        assert "gentle_smile" not in result
        assert "soft_lighting" not in result
        assert "masterpiece" not in result

    def test_strips_weighted_base_tokens(self):
        """Weighted scene tokens matching base tokens are stripped."""
        char = MagicMock()
        char.positive_prompt = "gentle_smile, brown_hair"

        scene_tags = ["(gentle_smile:1.15)", "(brown_hair:1.15)", "crying"]
        result = PromptBuilder._strip_char_base_from_scene(char, scene_tags)

        assert "crying" in result
        assert len([t for t in result if "gentle_smile" in t]) == 0
        assert len([t for t in result if "brown_hair" in t]) == 0

    def test_no_base_prompt_passthrough(self):
        """No positive_prompt → scene_tags returned as-is."""
        char = MagicMock()
        char.positive_prompt = None

        scene_tags = ["crying", "outdoors"]
        result = PromptBuilder._strip_char_base_from_scene(char, scene_tags)

        assert result == scene_tags

    def test_space_underscore_normalization(self):
        """Space-separated base tokens match underscore scene tokens."""
        char = MagicMock()
        char.positive_prompt = "gentle smile, soft lighting"

        scene_tags = ["gentle_smile", "soft_lighting", "crying"]
        result = PromptBuilder._strip_char_base_from_scene(char, scene_tags)

        assert "crying" in result
        assert "gentle_smile" not in result
        assert "soft_lighting" not in result

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_e2e_precomposed_prompt_dedup(self, mock_alias, mock_filter, mock_rule, builder):
        """Full pipeline: pre-composed prompt with char base tokens gets deduped."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        from models.tag import Tag

        gentle_tag = MagicMock(spec=Tag)
        gentle_tag.name = "gentle_smile"
        gentle_tag.default_layer = LAYER_EXPRESSION
        gentle_tag.usage_scope = "ANY"
        gentle_tag.group_name = "expression"

        crying_tag = MagicMock(spec=Tag)
        crying_tag.name = "crying"
        crying_tag.default_layer = LAYER_EXPRESSION
        crying_tag.usage_scope = "ANY"
        crying_tag.group_name = "expression"

        outdoors_tag = MagicMock(spec=Tag)
        outdoors_tag.name = "outdoors"
        outdoors_tag.default_layer = LAYER_ENVIRONMENT
        outdoors_tag.usage_scope = "ANY"
        outdoors_tag.group_name = "location_outdoor"

        all_tags = [gentle_tag, crying_tag, outdoors_tag]
        builder.db.query.return_value.filter.return_value.all.return_value = all_tags

        char = MagicMock()
        char.id = 1
        char.gender = "female"
        char.positive_prompt = "gentle_smile"
        char.tags = []
        char.loras = []

        builder.db.query.return_value.filter.return_value.first.return_value = char

        # Simulate frontend sending pre-composed prompt (includes gentle_smile from char base)
        precomposed_tokens = ["gentle_smile", "(crying:1.1)", "outdoors"]
        result = builder.compose_for_character(
            character_id=1,
            scene_tags=precomposed_tokens,
        )

        assert "(crying:1.1)" in result
        # gentle_smile should NOT appear — stripped from scene + overridden from char
        assert "gentle_smile" not in result
        assert "outdoors" in result


# ────────────────────────────────────────────
# Tier Ownership: quality_tags L0 injection
# ────────────────────────────────────────────


class TestQualityTagsL0Injection:
    """quality_tags 파라미터로 L0에 직접 배치 테스트."""

    def test_quality_tags_param_populates_l0(self, builder):
        """quality_tags 전달 시 L0에 배치 확인."""
        quality = ["RAW photo", "ultra realistic"]
        with patch.object(builder, "get_tag_info", return_value={}):
            result = builder.compose(["1girl"], quality_tags=quality)
        assert "RAW photo" in result
        assert "ultra realistic" in result
        # Quality tags는 프롬프트 앞쪽 (L0)에 위치해야 함
        raw_idx = result.find("RAW photo")
        girl_idx = result.find("1girl")
        assert raw_idx < girl_idx

    def test_ensure_quality_skips_when_l0_filled(self, builder):
        """L0이 이미 채워져 있으면 _ensure_quality_tags fallback 미주입."""
        layers = [["RAW photo"]] + [[] for _ in range(11)]
        PromptBuilder._ensure_quality_tags(layers)
        # FALLBACK_QUALITY_TAGS가 추가되지 않아야 함
        assert layers[LAYER_QUALITY] == ["RAW photo"]

    def test_quality_tags_in_compose_for_character(self, builder):
        """compose_for_character에서 quality_tags L0 배치 확인."""
        char = MagicMock()
        char.id = 1
        char.gender = "female"
        char.positive_prompt = None
        char.tags = []
        char.loras = []
        char.positive_prompt = None

        builder.db.query.return_value.filter.return_value.first.return_value = char

        quality = ["masterpiece", "best_quality"]
        with patch.object(builder, "get_tag_info", return_value={}):
            result = builder.compose_for_character(
                character_id=1,
                scene_tags=["smile", "outdoors"],
                quality_tags=quality,
            )
        assert "masterpiece" in result
        assert "best_quality" in result

    def test_quality_not_in_scene_tags_when_skip_quality(self):
        """skip_quality=True 시 _compose_positive에서 quality 미포함 확인."""
        from services.generation_style import _compose_positive

        ctx = MagicMock()
        ctx.default_positive = "masterpiece, best_quality"
        ctx.positive_embeddings = []

        result = _compose_positive(ctx, "1girl, smile", [], [], skip_quality=True)
        assert "masterpiece" not in result
        assert "1girl" in result

    def test_quality_included_when_skip_quality_false(self):
        """skip_quality=False(기본값) 시 quality tags 포함 확인."""
        from services.generation_style import _compose_positive

        ctx = MagicMock()
        ctx.default_positive = "masterpiece, best_quality"
        ctx.positive_embeddings = []

        result = _compose_positive(ctx, "1girl, smile", [], [])
        assert "masterpiece" in result
        assert "1girl" in result


# ────────────────────────────────────────────
# Tier Ownership: _collect_character_tags dedup
# ────────────────────────────────────────────


class TestCollectCharacterTagsDedup:
    """_collect_character_tags DB태그/positive_prompt 중복 제거 테스트."""

    def test_dedup_by_name(self, builder):
        """DB 태그와 positive_prompt에 동일 태그 → 1회만 수집."""
        char = MagicMock()
        char.gender = "female"
        char.positive_prompt = None
        char.loras = []

        # DB tag: brown_hair
        db_tag = MagicMock()
        db_tag.tag.name = "brown_hair"
        db_tag.tag.default_layer = 3
        db_tag.tag.group_name = "hair_color"
        db_tag.weight = 1.0
        db_tag.is_permanent = True
        char.tags = [db_tag]

        # positive_prompt: brown_hair (중복)
        char.positive_prompt = "brown_hair"

        with patch.object(
            builder, "get_tag_info", return_value={"brown_hair": {"layer": 3, "group_name": "hair_color"}}
        ):
            with patch("services.prompt.composition.TagFilterCache"):
                result = builder._collect_character_tags(char)

        # brown_hair는 1번만 수집되어야 함
        names = [r["name"] for r in result]
        assert names.count("brown_hair") == 1

    def test_custom_overrides_db_group(self, builder):
        """같은 group_name → custom이 DB를 대체."""
        char = MagicMock()
        char.gender = "female"
        char.positive_prompt = None
        char.loras = []

        # DB tag: brown_hair (hair_color group)
        db_tag = MagicMock()
        db_tag.tag.name = "brown_hair"
        db_tag.tag.default_layer = 3
        db_tag.tag.group_name = "hair_color"
        db_tag.weight = 1.0
        db_tag.is_permanent = True
        char.tags = [db_tag]

        # custom: blonde_hair (같은 hair_color group → DB 대체)
        char.positive_prompt = "blonde_hair"

        with patch("services.prompt.composition.TagFilterCache") as mock_fc:
            mock_fc.is_restricted.return_value = False
            with patch.object(
                builder,
                "get_tag_info",
                return_value={"blonde_hair": {"layer": 3, "group_name": "hair_color"}},
            ):
                result = builder._collect_character_tags(char)

        names = [r["name"] for r in result]
        assert "blonde_hair" in names
        assert "brown_hair" not in names


# ────────────────────────────────────────────
# Regression: SD_CLIENT_TYPE UnboundLocalError (#204)
# ────────────────────────────────────────────


class TestInjectLorasSDClientType:
    """SD_CLIENT_TYPE must be accessible even when no scene tag triggers a LoRA."""

    @patch("services.prompt.composition.LoRATriggerCache")
    def test_style_loras_without_scene_triggered_lora(self, mock_trigger_cache, builder):
        """style_loras present but no scene tag triggers a LoRA → no UnboundLocalError."""
        mock_trigger_cache.get_lora_name.return_value = None

        character = MagicMock()
        character.loras = []

        layers = [[] for _ in range(12)]
        style_loras = [{"name": "flat_color", "weight": 0.7, "trigger_words": ["flat color"]}]

        # This should NOT raise UnboundLocalError for SD_CLIENT_TYPE
        builder._inject_loras(character, [], layers, style_loras)

        all_tokens = [t for layer in layers for t in layer]
        assert any("<lora:flat_color:" in t for t in all_tokens)
