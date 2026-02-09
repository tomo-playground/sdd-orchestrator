"""Tests for V3PromptBuilder: _flatten_layers, _dedup_key, gender enhancement, conflict resolution."""

from unittest.mock import MagicMock, patch

import pytest

from services.prompt.v3_composition import (
    _CHARACTER_CAMERA_TAGS,
    CHARACTER_ONLY_LAYERS,
    EXCLUSIVE_GROUPS,  # noqa: F811
    LAYER_ACTION,
    LAYER_ATMOSPHERE,
    LAYER_CAMERA,
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
        assert "(smile:1.1)" in result
        assert "park" in result

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


# ────────────────────────────────────────────
# D-2: TagRuleCache conflict resolution tests
# ────────────────────────────────────────────


class TestConflictResolution:
    """Test TagRuleCache integration in _flatten_layers (D-2)."""

    @patch("services.prompt.v3_composition.TagRuleCache")
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

    @patch("services.prompt.v3_composition.TagRuleCache")
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

    @patch("services.prompt.v3_composition.TagFilterCache")
    def test_restricted_tags_filtered(self, mock_cache, builder):
        """Restricted tags should be filtered from custom_base_prompt."""
        from unittest.mock import MagicMock

        mock_cache.initialize.return_value = None
        mock_cache.is_restricted.side_effect = lambda tag: tag.lower() in {"kitchen", "outdoors"}

        # Mock character with custom_base_prompt containing restricted tags
        char = MagicMock()
        char.id = 1
        char.gender = "female"
        char.custom_base_prompt = "brown_hair, kitchen, long_hair, outdoors"
        char.tags = []
        char.loras = []
        char.prompt_mode = "standard"

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
        assert V3PromptBuilder._infer_layer_from_pattern("pink_hair") == LAYER_IDENTITY
        assert V3PromptBuilder._infer_layer_from_pattern("short_hair") == LAYER_IDENTITY

    def test_eyes_pattern_to_identity(self):
        """*_eyes tags → LAYER_IDENTITY."""
        assert V3PromptBuilder._infer_layer_from_pattern("blue_eyes") == LAYER_IDENTITY
        assert V3PromptBuilder._infer_layer_from_pattern("red_eyes") == LAYER_IDENTITY

    def test_action_pattern(self):
        """*ing tags → LAYER_ACTION."""
        assert V3PromptBuilder._infer_layer_from_pattern("running") == LAYER_ACTION
        assert V3PromptBuilder._infer_layer_from_pattern("walking") == LAYER_ACTION

    def test_action_pattern_excludes_earring(self):
        """earring should NOT be classified as action."""
        # "ring" ending should exclude -ring suffix
        result = V3PromptBuilder._infer_layer_from_pattern("earring")
        # earring should fall to LAYER_SUBJECT (default)
        assert result == LAYER_SUBJECT

    def test_camera_shot_pattern(self):
        """*_shot, *_view, from_* → LAYER_CAMERA."""
        assert V3PromptBuilder._infer_layer_from_pattern("wide_shot") == LAYER_CAMERA
        assert V3PromptBuilder._infer_layer_from_pattern("top_view") == LAYER_CAMERA
        assert V3PromptBuilder._infer_layer_from_pattern("from_above") == LAYER_CAMERA

    def test_expression_keywords(self):
        """Known expression keywords → LAYER_EXPRESSION."""
        assert V3PromptBuilder._infer_layer_from_pattern("smiling") == LAYER_EXPRESSION
        assert V3PromptBuilder._infer_layer_from_pattern("crying") == LAYER_EXPRESSION

    def test_unknown_tag_defaults_to_subject(self):
        """Unknown pattern → LAYER_SUBJECT."""
        assert V3PromptBuilder._infer_layer_from_pattern("unknown_tag") == LAYER_SUBJECT
        assert V3PromptBuilder._infer_layer_from_pattern("mystery") == LAYER_SUBJECT


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
                n: scene_info[n]
                for n in [t.lower().replace(" ", "_").strip() for t in names]
                if n in scene_info
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
    """Verify EXCLUSIVE_GROUPS contains expected groups."""

    def test_contains_expected_groups(self):
        assert "hair_color" in EXCLUSIVE_GROUPS
        assert "eye_color" in EXCLUSIVE_GROUPS
        assert "hair_length" in EXCLUSIVE_GROUPS
        assert "skin_color" in EXCLUSIVE_GROUPS

    def test_does_not_contain_hair_style(self):
        assert "hair_style" not in EXCLUSIVE_GROUPS

    def test_does_not_contain_clothing(self):
        assert "clothing" not in EXCLUSIVE_GROUPS


# ────────────────────────────────────────────
# _inject_loras dedup tests
# ────────────────────────────────────────────


class TestInjectLorasDedup:
    """Test _inject_loras dedup: scene-triggered + style_loras with same name."""

    @patch("services.prompt.v3_composition.LoRATriggerCache")
    def test_inject_loras_no_duplicate_style_lora(self, mock_trigger_cache, builder):
        """Scene-triggered + style_loras with same name → only one <lora:> tag."""
        # Scene tag "flat_color" triggers LoRA via cache
        mock_trigger_cache.get_lora_name.side_effect = lambda tag: "flat_color" if tag == "flat_color" else None

        # Mock _get_lora_info for scene-triggered lookup
        builder._get_lora_info = MagicMock(return_value=(0.6, "style"))

        character = MagicMock()
        character.loras = []
        character.prompt_mode = "standard"

        layers = [[] for _ in range(12)]
        scene_tags = ["flat_color", "outdoors"]

        # style_loras also includes flat_color (would be duplicate)
        style_loras = [{"name": "flat_color", "weight": 0.6, "trigger_words": []}]

        builder._inject_loras(character, scene_tags, layers, style_loras)

        # Count lora tags across all layers
        all_tokens = [t for layer in layers for t in layer]
        lora_count = sum(1 for t in all_tokens if "<lora:flat_color:" in t)
        assert lora_count == 1, f"Expected 1 flat_color LoRA tag, got {lora_count}: {all_tokens}"

    @patch("services.prompt.v3_composition.LoRATriggerCache")
    def test_inject_loras_style_lora_added_when_not_triggered(self, mock_trigger_cache, builder):
        """style_loras not in scene tags → still added normally."""
        mock_trigger_cache.get_lora_name.return_value = None

        character = MagicMock()
        character.loras = []
        character.prompt_mode = "standard"

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
        assert V3PromptBuilder._is_background_scene(["no_humans", "scenery", "cafe"])
        assert V3PromptBuilder._is_background_scene(["scenery", "no_humans"])
        # Case/whitespace insensitive
        assert V3PromptBuilder._is_background_scene(["No_Humans", "park"])
        assert V3PromptBuilder._is_background_scene(["no humans", "park"])

    def test_is_background_scene_negative(self):
        """Scenes without no_humans are not background scenes."""
        assert not V3PromptBuilder._is_background_scene(["1girl", "standing", "cafe"])
        assert not V3PromptBuilder._is_background_scene(["scenery", "outdoors"])
        assert not V3PromptBuilder._is_background_scene([])

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
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

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
    def test_compose_for_character_background_skips_character(self, mock_alias, mock_rule, builder):
        """compose_for_character with no_humans skips character DB query."""
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        # Mock tag DB to return proper layers
        builder.get_tag_info = MagicMock(
            return_value={
                "no_humans": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
                "scenery": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
                "library": {"layer": LAYER_ENVIRONMENT, "scope": "ANY", "group_name": None},
            }
        )

        result = builder.compose_for_character(
            character_id=999,
            scene_tags=["no_humans", "scenery", "library"],
        )

        # Should not query Character table (no_humans early exit)
        builder.db.query.return_value.filter.return_value.first.assert_not_called()

        assert "no_humans" in result
        assert "library" in result

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
    def test_background_scene_keeps_style_loras(self, mock_alias, mock_rule, builder):
        """Background scene preserves style LoRAs for visual consistency."""
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
        assert "flat color" in result

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
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

        V3PromptBuilder._strip_character_layers(layers)

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
        """_CHARACTER_CAMERA_TAGS contains expected framing tags."""
        expected = {"cowboy_shot", "upper_body", "portrait", "close-up", "close_up", "full_body"}
        assert expected.issubset(_CHARACTER_CAMERA_TAGS)

    @patch("services.prompt.v3_composition.LoRATriggerCache")
    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
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


# ────────────────────────────────────────────
# LoRA Weight Cap tests
# ────────────────────────────────────────────


class TestLoRAWeightCap:
    """Test STYLE_LORA_WEIGHT_CAP applied at V3 composition time (SSOT)."""

    @patch("services.prompt.v3_composition.LoRATriggerCache")
    def test_cap_applied_to_character_lora(self, mock_trigger_cache, builder):
        """Character LoRA weight 0.89 → capped to 0.76."""
        mock_trigger_cache.get_lora_name.return_value = None

        character = MagicMock()
        character.prompt_mode = "lora"
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
        assert "<lora:char_lora:0.76>" in all_tokens
        assert "<lora:char_lora:0.89>" not in all_tokens

    @patch("services.prompt.v3_composition.LoRATriggerCache")
    def test_cap_applied_to_style_lora(self, mock_trigger_cache, builder):
        """Style LoRA weight 0.9 → capped to 0.76."""
        mock_trigger_cache.get_lora_name.return_value = None

        character = MagicMock()
        character.loras = []
        character.prompt_mode = "standard"

        layers = [[] for _ in range(12)]
        style_loras = [{"name": "style_lora", "weight": 0.9, "trigger_words": []}]

        builder._inject_loras(character, [], layers, style_loras)

        all_tokens = [t for layer in layers for t in layer]
        assert "<lora:style_lora:0.76>" in all_tokens
        assert "<lora:style_lora:0.9>" not in all_tokens

    @patch("services.prompt.v3_composition.LoRATriggerCache")
    def test_cap_applied_to_scene_triggered_lora(self, mock_trigger_cache, builder):
        """Scene-triggered LoRA weight 0.85 → capped to 0.76."""
        mock_trigger_cache.get_lora_name.side_effect = lambda tag: "scene_lora" if tag == "trigger_tag" else None
        builder._get_lora_info = MagicMock(return_value=(0.85, "character"))

        character = MagicMock()
        character.loras = []
        character.prompt_mode = "standard"

        layers = [[] for _ in range(12)]
        builder._inject_loras(character, ["trigger_tag"], layers, None)

        all_tokens = [t for layer in layers for t in layer]
        assert "<lora:scene_lora:0.76>" in all_tokens
        assert "<lora:scene_lora:0.85>" not in all_tokens

    @patch("services.prompt.v3_composition.LoRATriggerCache")
    def test_weight_below_cap_preserved(self, mock_trigger_cache, builder):
        """Weight 0.65 (below cap) → preserved as-is."""
        mock_trigger_cache.get_lora_name.return_value = None

        character = MagicMock()
        character.loras = []
        character.prompt_mode = "standard"

        layers = [[] for _ in range(12)]
        style_loras = [{"name": "mild_lora", "weight": 0.65, "trigger_words": []}]

        builder._inject_loras(character, [], layers, style_loras)

        all_tokens = [t for layer in layers for t in layer]
        assert "<lora:mild_lora:0.65>" in all_tokens

    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
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

    @patch("services.prompt.v3_composition.LoRATriggerCache")
    @patch("services.prompt.v3_composition.TagRuleCache")
    @patch("services.prompt.v3_composition.TagAliasCache")
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
        assert V3PromptBuilder._cap_lora_weight(0.7) == 0.7

    def test_cap_static_method(self):
        """_cap_lora_weight caps at STYLE_LORA_WEIGHT_CAP."""
        assert V3PromptBuilder._cap_lora_weight(0.89) == 0.76
        assert V3PromptBuilder._cap_lora_weight(0.76) == 0.76
        assert V3PromptBuilder._cap_lora_weight(0.5) == 0.5
