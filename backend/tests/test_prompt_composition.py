"""Integration tests for 9.8 Prompt Composition System.

Tests 4 scenarios as defined in PROMPT_SPEC.md:
1. Standard Mode - No LoRA
2. Standard Mode - Style LoRA only
3. LoRA Mode - Character LoRA
4. LoRA Mode - Complex scene with multiple LoRAs
"""

import pytest

from services.prompt_composition import (
    calculate_lora_weight,
    compose_prompt_string,
    compose_prompt_tokens,
    deduplicate_triggers,
    detect_scene_complexity,
    ensure_quality_tags,
    filter_conflicting_tokens,
    get_effective_mode_from_dict,
    get_token_category,
    get_token_priority,
    insert_break_token,
    sort_prompt_tokens,
)


class TestTokenCategory:
    """Tests for get_token_category()."""

    def test_quality_tokens(self):
        assert get_token_category("masterpiece") == "quality"
        assert get_token_category("best quality") == "quality"
        assert get_token_category("high quality") == "quality"

    def test_subject_tokens(self):
        assert get_token_category("1girl") == "subject"
        assert get_token_category("1boy") == "subject"
        assert get_token_category("solo") == "subject"

    def test_appearance_tokens(self):
        assert get_token_category("blue hair") == "hair_color"
        assert get_token_category("long hair") == "hair_length"
        assert get_token_category("ponytail") == "hair_style"
        assert get_token_category("blue eyes") == "eye_color"

    def test_expression_tokens(self):
        assert get_token_category("smiling") == "expression"
        assert get_token_category("crying") == "expression"
        assert get_token_category("blush") == "expression"

    def test_pose_action_tokens(self):
        assert get_token_category("standing") == "pose"
        assert get_token_category("sitting") == "pose"
        assert get_token_category("running") == "action"
        assert get_token_category("walking") == "action"

    def test_camera_tokens(self):
        assert get_token_category("from above") == "camera"
        assert get_token_category("full body") == "camera"
        assert get_token_category("close-up") == "camera"

    def test_location_tokens(self):
        assert get_token_category("bedroom") == "location_indoor"
        assert get_token_category("forest") == "location_outdoor"

    def test_unknown_token(self):
        assert get_token_category("random_unknown_token") is None


class TestTokenPriority:
    """Tests for get_token_priority()."""

    def test_priority_order(self):
        assert get_token_priority("masterpiece") < get_token_priority("1girl")
        assert get_token_priority("1girl") < get_token_priority("smiling")
        assert get_token_priority("smiling") < get_token_priority("bedroom")

    def test_unknown_token_low_priority(self):
        assert get_token_priority("random_token") == 99


class TestSceneComplexity:
    """Tests for detect_scene_complexity()."""

    def test_simple_scene(self):
        tokens = ["1girl", "smiling"]
        assert detect_scene_complexity(tokens) == "simple"

    def test_moderate_scene(self):
        tokens = ["1girl", "smiling", "looking at viewer", "standing", "bedroom"]
        assert detect_scene_complexity(tokens) == "moderate"

    def test_complex_scene(self):
        tokens = [
            "1girl", "smiling", "looking at viewer", "standing",
            "running", "from above", "bedroom", "sunset", "warm lighting"
        ]
        assert detect_scene_complexity(tokens) == "complex"


class TestLoRAWeight:
    """Tests for calculate_lora_weight()."""

    def test_character_lora_weights(self):
        assert calculate_lora_weight("character", "simple") == 0.6
        assert calculate_lora_weight("character", "moderate") == 0.5
        assert calculate_lora_weight("character", "complex") == 0.4

    def test_style_lora_weights(self):
        assert calculate_lora_weight("style", "simple") == 0.6
        assert calculate_lora_weight("style", "moderate") == 0.5
        assert calculate_lora_weight("style", "complex") == 0.4

    def test_optimal_weight_cap(self):
        # Optimal weight should cap the calculated weight
        assert calculate_lora_weight("character", "simple", optimal_weight=0.45) == 0.45
        # But not increase it
        assert calculate_lora_weight("character", "complex", optimal_weight=0.8) == 0.4


class TestEffectiveMode:
    """Tests for get_effective_mode_from_dict()."""

    def test_explicit_standard(self):
        assert get_effective_mode_from_dict("standard", None) == "standard"
        assert get_effective_mode_from_dict("standard", [{"lora_type": "character"}]) == "standard"

    def test_explicit_lora(self):
        assert get_effective_mode_from_dict("lora", None) == "lora"
        assert get_effective_mode_from_dict("lora", []) == "lora"

    def test_auto_no_loras(self):
        assert get_effective_mode_from_dict("auto", None) == "standard"
        assert get_effective_mode_from_dict("auto", []) == "standard"

    def test_auto_style_lora(self):
        loras = [{"lora_type": "style"}]
        assert get_effective_mode_from_dict("auto", loras) == "standard"

    def test_auto_character_lora(self):
        loras = [{"lora_type": "character"}]
        assert get_effective_mode_from_dict("auto", loras) == "lora"


class TestConflictFiltering:
    """Tests for filter_conflicting_tokens()."""

    def test_duplicate_removal(self):
        tokens = ["1girl", "smiling", "1girl"]
        result = filter_conflicting_tokens(tokens)
        assert result.count("1girl") == 1

    def test_location_conflict(self):
        tokens = ["bedroom", "forest"]  # indoor vs outdoor
        result = filter_conflicting_tokens(tokens)
        assert "bedroom" in result
        assert "forest" not in result

    def test_location_indoor_outdoor_conflict(self):
        """Test indoors vs street conflict (user-reported bug case)."""
        tokens = ["indoors", "street", "room", "cafe"]
        result = filter_conflicting_tokens(tokens)
        # First location (indoors) should win, all others removed
        assert "indoors" in result
        assert "street" not in result  # outdoor, conflicts with indoors
        assert "room" not in result    # indoor, but duplicate location
        assert "cafe" not in result    # indoor, but duplicate location

    def test_multiple_indoor_locations(self):
        """Only first indoor location should be kept."""
        tokens = ["library", "bedroom", "cafe"]
        result = filter_conflicting_tokens(tokens)
        assert "library" in result
        assert "bedroom" not in result
        assert "cafe" not in result

    def test_hair_length_conflict(self):
        tokens = ["short hair", "long hair"]
        result = filter_conflicting_tokens(tokens)
        assert len(result) == 1
        assert "short hair" in result


class TestQualityTags:
    """Tests for ensure_quality_tags()."""

    def test_add_quality_tags(self):
        tokens = ["1girl", "smiling"]
        result = ensure_quality_tags(tokens)
        assert result[0] == "masterpiece"
        assert result[1] == "best quality"

    def test_preserve_existing_quality(self):
        tokens = ["masterpiece", "1girl"]
        result = ensure_quality_tags(tokens)
        assert result == tokens


class TestBreakToken:
    """Tests for insert_break_token()."""

    def test_break_insertion(self):
        tokens = ["masterpiece", "1girl", "smiling", "standing", "bedroom"]
        result = insert_break_token(tokens, after_category="action")
        assert "BREAK" in result


class TestTokenSorting:
    """Tests for sort_prompt_tokens()."""

    def test_standard_mode_order(self):
        tokens = ["bedroom", "1girl", "smiling", "masterpiece"]
        result = sort_prompt_tokens(tokens, "standard")
        assert result[0] == "masterpiece"
        assert result[1] == "1girl"

    def test_lora_mode_order(self):
        tokens = ["blue hair", "1girl", "smiling", "masterpiece"]
        result = sort_prompt_tokens(tokens, "lora")
        # In LoRA mode, scene (expression) comes before appearance (hair)
        smiling_idx = result.index("smiling")
        hair_idx = result.index("blue hair")
        assert smiling_idx < hair_idx


class TestPromptComposition:
    """Integration tests for full prompt composition."""

    def test_scenario_1_standard_no_lora(self):
        """Scenario 1: Standard Mode - No LoRA."""
        tokens = ["1girl", "smiling", "blue hair", "bedroom"]
        result = compose_prompt_string(tokens, "standard")

        # Should have quality tags
        assert "masterpiece" in result
        # Order: quality → subject → appearance → scene
        parts = result.split(", ")
        assert parts.index("masterpiece") < parts.index("1girl")
        assert parts.index("1girl") < parts.index("smiling")

    def test_scenario_2_standard_style_lora(self):
        """Scenario 2: Standard Mode - Style LoRA only."""
        tokens = ["1girl", "smiling", "bedroom"]
        lora_strs = ["<lora:chibi:0.5>"]

        result = compose_prompt_string(
            tokens, "standard",
            lora_strings=lora_strs
        )

        assert "<lora:chibi:0.5>" in result
        # No BREAK in standard mode
        assert "BREAK" not in result

    def test_scenario_3_lora_mode_character(self):
        """Scenario 3: LoRA Mode - Character LoRA."""
        tokens = ["1girl", "smiling", "standing", "bedroom"]
        lora_strs = ["<lora:eureka:0.5>"]
        triggers = ["eureka"]

        result = compose_prompt_string(
            tokens, "lora",
            lora_strings=lora_strs,
            trigger_words=triggers,
            use_break=True
        )

        assert "<lora:eureka:0.5>" in result
        assert "BREAK" in result

    def test_scenario_4_lora_mode_complex(self):
        """Scenario 4: LoRA Mode - Complex scene."""
        tokens = [
            "1girl", "smiling", "looking at viewer", "standing",
            "running", "from above", "bedroom", "sunset", "warm lighting"
        ]
        lora_strs = ["<lora:midoriya:0.4>"]

        result = compose_prompt_tokens(
            tokens, "lora",
            lora_strings=lora_strs,
            use_break=True
        )

        assert "<lora:midoriya:0.4>" in result
        assert "BREAK" in result
        # Quality tags should be added
        assert "masterpiece" in result


class TestTriggerDeduplication:
    """Tests for trigger word deduplication."""

    def test_deduplicate_existing_trigger(self):
        tokens = ["eureka", "smiling"]
        triggers = ["eureka", "pink hair"]

        result = deduplicate_triggers(tokens, triggers)
        assert "eureka" not in result
        assert "pink hair" in result

    def test_keep_unique_triggers(self):
        tokens = ["smiling", "bedroom"]
        triggers = ["eureka", "pink hair"]

        result = deduplicate_triggers(tokens, triggers)
        assert len(result) == 2
