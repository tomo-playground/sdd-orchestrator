"""Tests for PromptBuilder.compose_for_reference() — reference image prompt composition."""

from unittest.mock import MagicMock, patch

import pytest

from services.prompt.composition import (
    LAYER_CAMERA,
    LAYER_QUALITY,
    PromptBuilder,
)


@pytest.fixture
def builder():
    """Create PromptBuilder with mocked DB session."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.first.return_value = None
    return PromptBuilder(mock_db)


def _make_character(
    gender=None,
    loras=None,
    positive_prompt=None,
):
    """Helper to build a mock Character."""
    char = MagicMock()
    char.gender = gender
    char.loras = loras or []
    char.positive_prompt = positive_prompt
    char.tags = []
    return char


# ────────────────────────────────────────────
# Quality tags
# ────────────────────────────────────────────


class TestReferenceQualityTags:
    """compose_for_reference must include masterpiece + best_quality."""

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
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
# Environment tags (no forced background)
# ────────────────────────────────────────────


class TestReferenceEnvironmentTags:
    """Reference images should NOT force white_background (natural background)."""

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_no_forced_background(self, mock_alias, mock_filter, mock_rule, builder):
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        char = _make_character()
        result = builder.compose_for_reference(char)

        assert "white_background" not in result
        assert "simple_background" not in result

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
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

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
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
    """Style LoRAs should be scaled by REFERENCE_STYLE_LORA_SCALE."""

    @patch("config.REFERENCE_STYLE_LORA_SCALE", 0.45)
    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
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
        lora_obj.default_weight = 0.65
        builder.db.query.return_value.filter.return_value.all.return_value = [lora_obj]

        char = _make_character(loras=[{"lora_id": 2, "weight": 0.7}])
        result = builder.compose_for_reference(char)

        # Style LoRA: 0.7 × REFERENCE_STYLE_LORA_SCALE(0.45) = 0.32
        assert "<lora:flat_color:0.32>" in result

    @patch("config.REFERENCE_STYLE_LORA_SCALE", 0.45)
    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_style_lora_capped(self, mock_alias, mock_filter, mock_rule, builder):
        """Style LoRA weight 0.9 × 0.45 = 0.41 (below cap)."""
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
        lora_obj.default_weight = None
        builder.db.query.return_value.filter.return_value.all.return_value = [lora_obj]

        char = _make_character(loras=[{"lora_id": 2, "weight": 0.9}])
        result = builder.compose_for_reference(char)

        # Style LoRA: 0.9 × REFERENCE_STYLE_LORA_SCALE(0.45) = 0.41 (below cap)
        assert "<lora:flat_color:0.41>" in result
        assert "<lora:flat_color:0.9>" not in result


# ────────────────────────────────────────────
# Tag deduplication
# ────────────────────────────────────────────


class TestReferenceDedup:
    """Tags should not appear duplicated in the final prompt."""

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
    def test_no_duplicate_tags(self, mock_alias, mock_filter, mock_rule, builder):
        mock_alias.initialize.return_value = None
        mock_alias.get_replacement.return_value = ...
        mock_filter.initialize.return_value = None
        mock_filter.is_restricted.return_value = False
        mock_rule.initialize.return_value = None
        mock_rule.is_conflicting.return_value = False

        # Character with tag that also appears in positive_prompt
        char_tag = MagicMock()
        char_tag.tag = MagicMock()
        char_tag.tag.name = "solo"
        char_tag.tag.default_layer = LAYER_CAMERA
        char_tag.weight = 1.0

        char = _make_character(positive_prompt="solo, white_background")
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

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
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

    @patch("services.prompt.composition.TagRuleCache")
    @patch("services.prompt.composition.TagFilterCache")
    @patch("services.prompt.composition.TagAliasCache")
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
# _inject_reference_defaults
# ────────────────────────────────────────────


class TestInjectReferenceDefaults:
    """Test _inject_reference_defaults helper."""

    def test_injects_camera_only(self, builder):
        layers = [[] for _ in range(12)]
        builder._inject_reference_defaults(layers)

        # ENV_TAGS is empty — no background forced
        quality = layers[LAYER_QUALITY]
        assert not any("white_background" in t for t in quality)
        # Camera tags still injected
        assert any("solo" in t for t in layers[LAYER_CAMERA])
        assert any("looking_at_viewer" in t for t in layers[LAYER_CAMERA])

    def test_uses_style_ctx_env_tags(self, builder):
        """StyleContext의 reference_env_tags가 전역 상수보다 우선한다."""
        from services.style_context import StyleContext

        ctx = StyleContext(
            profile_id=1,
            profile_name="test",
            reference_env_tags=["(gray_background:1.5)", "studio_lighting"],
        )
        layers = [[] for _ in range(12)]
        builder._inject_reference_defaults(layers, style_ctx=ctx)

        quality = layers[LAYER_QUALITY]
        assert "(gray_background:1.5)" in quality
        assert "studio_lighting" in quality
        # 전역 폴백 태그가 없어야 함
        assert "white_background" not in quality

    def test_uses_style_ctx_camera_tags(self, builder):
        """StyleContext의 reference_camera_tags가 전역 상수보다 우선한다."""
        from services.style_context import StyleContext

        ctx = StyleContext(
            profile_id=1,
            profile_name="test",
            reference_camera_tags=["(solo:1.3)", "upper_body"],
        )
        layers = [[] for _ in range(12)]
        builder._inject_reference_defaults(layers, style_ctx=ctx)

        camera = layers[LAYER_CAMERA]
        assert "(solo:1.3)" in camera
        assert "upper_body" in camera
        # 전역 폴백의 full_body가 없어야 함
        assert "full_body" not in camera

    def test_empty_list_skips_injection(self, builder):
        """빈 배열 []은 의도적 비활성화 — 태그 주입 안 함."""
        from services.style_context import StyleContext

        ctx = StyleContext(
            profile_id=1,
            profile_name="test",
            reference_env_tags=[],
            reference_camera_tags=[],
        )
        layers = [[] for _ in range(12)]
        builder._inject_reference_defaults(layers, style_ctx=ctx)

        assert layers[LAYER_QUALITY] == []
        assert layers[LAYER_CAMERA] == []

    def test_none_falls_back_to_global(self, builder):
        """style_ctx 필드가 None이면 전역 상수로 폴백."""
        from services.style_context import StyleContext

        ctx = StyleContext(
            profile_id=1,
            profile_name="test",
            reference_env_tags=None,
            reference_camera_tags=None,
        )
        layers = [[] for _ in range(12)]
        builder._inject_reference_defaults(layers, style_ctx=ctx)

        # 전역 REFERENCE_ENV_TAGS = [] (no background forced)
        assert not any("white_background" in t for t in layers[LAYER_QUALITY])
        # 전역 REFERENCE_CAMERA_TAGS 폴백
        assert any("solo" in t for t in layers[LAYER_CAMERA])

    def test_no_duplicate_if_already_present(self, builder):
        layers = [[] for _ in range(12)]
        layers[LAYER_CAMERA] = ["solo"]

        builder._inject_reference_defaults(layers)

        assert layers[LAYER_CAMERA].count("solo") == 1
