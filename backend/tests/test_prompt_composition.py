"""Integration tests for 9.8 Prompt Composition System.

Tests 4 scenarios as defined in PROMPT_SPEC.md:
1. Standard Mode - No LoRA
2. Standard Mode - Style LoRA only
3. LoRA Mode - Character LoRA
4. LoRA Mode - Complex scene with multiple LoRAs
"""


from services.prompt_composition import (
    _deduplicate_loras,
    _normalize_break_tokens,
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

    def test_ocean_with_indoor_locations(self):
        """Test user-reported case: ocean (outdoor) + library/room/street/cafe."""
        tokens = ["smile", "ocean", "daytime", "library", "room", "street", "cafe"]
        result = filter_conflicting_tokens(tokens)
        # ocean is first location (outdoor) - should be kept
        assert "ocean" in result
        # All other locations should be removed
        assert "library" not in result  # indoor, conflicts with outdoor
        assert "room" not in result     # indoor, conflicts with outdoor
        assert "street" not in result   # outdoor, but duplicate location
        assert "cafe" not in result     # indoor, conflicts with outdoor
        # Non-location tokens should remain
        assert "smile" in result
        assert "daytime" in result

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


class TestLoRADeduplication:
    """Tests for LoRA string deduplication (Bug fix 2026-01-26)."""

    def test_duplicate_lora_same_weight(self):
        """Same LoRA with same weight should be deduplicated."""
        loras = ["<lora:midoriya:0.5>", "<lora:midoriya:0.5>"]
        result = _deduplicate_loras(loras)
        assert len(result) == 1
        assert result[0] == "<lora:midoriya:0.5>"

    def test_duplicate_lora_different_weight(self):
        """Same LoRA with different weights - last weight wins."""
        loras = ["<lora:midoriya:0.4>", "<lora:midoriya:0.5>"]
        result = _deduplicate_loras(loras)
        assert len(result) == 1
        assert result[0] == "<lora:midoriya:0.5>"

    def test_multiple_different_loras(self):
        """Different LoRAs should all be kept."""
        loras = ["<lora:midoriya:0.5>", "<lora:eureka:0.6>", "<lora:chibi:0.4>"]
        result = _deduplicate_loras(loras)
        assert len(result) == 3

    def test_mixed_duplicate_loras(self):
        """Mix of duplicate and unique LoRAs."""
        loras = [
            "<lora:midoriya:0.4>",
            "<lora:eureka:0.6>",
            "<lora:midoriya:0.5>",  # Duplicate, should replace 0.4
        ]
        result = _deduplicate_loras(loras)
        assert len(result) == 2
        assert "<lora:midoriya:0.5>" in result
        assert "<lora:eureka:0.6>" in result

    def test_empty_lora_list(self):
        """Empty list should return empty."""
        assert _deduplicate_loras([]) == []
        assert _deduplicate_loras(None) == []


class TestBreakNormalization:
    """Tests for BREAK token normalization (Bug fix 2026-01-26)."""

    def test_lowercase_break_normalized(self):
        """Lowercase 'break' should become 'BREAK'."""
        tokens = ["smile", "break", "sitting"]
        result = _normalize_break_tokens(tokens)
        assert "break" not in result
        assert "BREAK" in result

    def test_multiple_breaks_deduplicated(self):
        """Multiple BREAK tokens should become one."""
        tokens = ["smile", "BREAK", "break", "BREAK", "sitting"]
        result = _normalize_break_tokens(tokens)
        assert result.count("BREAK") == 1

    def test_mixed_case_breaks(self):
        """All case variations should be normalized."""
        tokens = ["smile", "break", "BREAK", "Break", "sitting"]
        result = _normalize_break_tokens(tokens)
        assert result.count("BREAK") == 1
        assert "break" not in result
        assert "Break" not in result

    def test_no_break_unchanged(self):
        """Tokens without BREAK should be unchanged."""
        tokens = ["smile", "sitting", "indoors"]
        result = _normalize_break_tokens(tokens)
        assert result == tokens


class TestCameraConflict:
    """Tests for camera angle/shot type conflicts (Bug fix 2026-01-26)."""

    def test_medium_shot_recognized(self):
        """medium shot should be recognized as camera category."""
        assert get_token_category("medium shot") == "camera"

    def test_camera_shot_conflict(self):
        """Only one camera shot type should remain."""
        tokens = ["full body", "medium shot", "close-up"]
        result = filter_conflicting_tokens(tokens)
        assert len(result) == 1
        assert "full body" in result

    def test_camera_angle_conflict(self):
        """Only one camera angle should remain."""
        tokens = ["from above", "from below", "side view"]
        result = filter_conflicting_tokens(tokens)
        assert len(result) == 1
        assert "from above" in result

    def test_mixed_camera_tokens(self):
        """Mixed shot types and angles - first wins."""
        tokens = ["portrait", "from above", "wide shot"]
        result = filter_conflicting_tokens(tokens)
        assert "portrait" in result
        assert "from above" not in result
        assert "wide shot" not in result


class TestFullCompositionBugFixes:
    """Integration tests for all bug fixes (2026-01-26)."""

    def test_user_reported_bug_full_case(self):
        """Full reproduction of user-reported bug."""
        tokens = [
            "smile", "looking at viewer", "sitting", "playing guitar",
            "full body", "indoors", "library", "room", "street", "cafe",
            "break", "midoriya izuku", "short green hair", "medium shot"
        ]
        loras = ["<lora:mha_midoriya-10:0.4>", "<lora:mha_midoriya-10:0.5>"]
        triggers = ["midoriya izuku"]

        result = compose_prompt_tokens(
            tokens, "lora",
            lora_strings=loras,
            trigger_words=triggers,
            use_break=True
        )

        # LoRA should be deduplicated (only one)
        lora_count = sum(1 for t in result if t.startswith("<lora:mha_midoriya"))
        assert lora_count == 1

        # BREAK should be normalized and singular
        assert result.count("BREAK") == 1
        assert "break" not in result

        # Location should be filtered (only first indoor remains)
        location_tokens = ["indoors", "library", "room", "street", "cafe"]
        locations_in_result = [t for t in result if t in location_tokens]
        assert len(locations_in_result) == 1

        # Camera should be filtered (only first)
        camera_tokens = ["full body", "medium shot"]
        cameras_in_result = [t for t in result if t in camera_tokens]
        assert len(cameras_in_result) == 1

    def test_composition_with_user_break(self):
        """User-provided BREAK should not create duplicate."""
        tokens = ["smile", "BREAK", "indoors"]
        result = compose_prompt_tokens(
            tokens, "lora",
            use_break=True
        )
        assert result.count("BREAK") == 1

    def test_composition_lora_weight_preserved(self):
        """Last LoRA weight should be preserved after deduplication."""
        tokens = ["smile", "sitting"]
        loras = ["<lora:test:0.3>", "<lora:test:0.7>"]

        result = compose_prompt_tokens(
            tokens, "lora",
            lora_strings=loras
        )

        assert "<lora:test:0.7>" in result
        assert "<lora:test:0.3>" not in result


class TestLoRAExtractionFromTokens:
    """Tests for LoRA extraction from tokens (Bug fix 2026-01-26)."""

    def test_lora_in_tokens_merged_with_lora_strings(self):
        """LoRAs in tokens should be extracted and merged with lora_strings."""
        tokens = ["smile", "<lora:midoriya:0.4>", "indoors"]
        loras = ["<lora:eureka:0.6>"]

        result = compose_prompt_tokens(
            tokens, "lora",
            lora_strings=loras,
            use_break=False
        )

        # Both LoRAs should be present
        assert any("midoriya" in t for t in result)
        assert any("eureka" in t for t in result)
        # But no duplicates
        midoriya_count = sum(1 for t in result if "midoriya" in t)
        assert midoriya_count == 1

    def test_lora_in_tokens_dedup_with_lora_strings(self):
        """Same LoRA in tokens and lora_strings should be deduplicated."""
        tokens = ["smile", "<lora:midoriya:0.4>", "sitting"]
        loras = ["<lora:midoriya:0.5>"]  # Same LoRA, different weight

        result = compose_prompt_tokens(
            tokens, "lora",
            lora_strings=loras,
            use_break=False
        )

        # Only one midoriya LoRA
        midoriya_count = sum(1 for t in result if "midoriya" in t)
        assert midoriya_count == 1

    def test_multiple_loras_in_tokens(self):
        """Multiple LoRAs in tokens should all be extracted."""
        tokens = ["smile", "<lora:a:0.3>", "<lora:b:0.4>", "sitting"]
        loras = ["<lora:c:0.5>"]

        result = compose_prompt_tokens(
            tokens, "lora",
            lora_strings=loras,
            use_break=False
        )

        # All 3 LoRAs should be present
        assert any("lora:a" in t for t in result)
        assert any("lora:b" in t for t in result)
        assert any("lora:c" in t for t in result)

    def test_no_lora_in_tokens(self):
        """No LoRA in tokens should work normally."""
        tokens = ["smile", "sitting"]
        loras = ["<lora:test:0.5>"]

        result = compose_prompt_tokens(
            tokens, "lora",
            lora_strings=loras,
            use_break=False
        )

        assert "<lora:test:0.5>" in result


class TestExpressionConflict:
    """Tests for expression and gaze conflict filtering."""

    def test_crying_vs_laughing(self):
        """crying and laughing should not coexist."""
        tokens = ["crying", "looking down", "standing", "laughing"]
        result = filter_conflicting_tokens(tokens)
        assert "crying" in result
        assert "laughing" not in result

    def test_sad_vs_happy(self):
        """sad and happy should not coexist."""
        tokens = ["sad", "standing", "happy", "smile"]
        result = filter_conflicting_tokens(tokens)
        assert "sad" in result
        assert "happy" not in result
        assert "smile" not in result

    def test_angry_vs_smile(self):
        """angry and smile should not coexist."""
        tokens = ["angry", "standing", "smile"]
        result = filter_conflicting_tokens(tokens)
        assert "angry" in result
        assert "smile" not in result

    def test_expression_category_only_one(self):
        """Only one expression should remain."""
        tokens = ["crying", "sad", "angry", "happy"]
        result = filter_conflicting_tokens(tokens)
        assert result == ["crying"]


class TestGazeConflict:
    """Tests for gaze direction conflicts."""

    def test_looking_down_vs_up(self):
        """looking down and looking up should not coexist."""
        tokens = ["looking down", "standing", "looking up"]
        result = filter_conflicting_tokens(tokens)
        assert "looking down" in result
        assert "looking up" not in result

    def test_looking_away_vs_at_viewer(self):
        """looking away and looking at viewer conflict."""
        tokens = ["looking away", "smile", "looking at viewer"]
        result = filter_conflicting_tokens(tokens)
        assert "looking away" in result
        assert "looking at viewer" not in result


class TestPoseConflict:
    """Tests for pose conflicts."""

    def test_sitting_vs_standing(self):
        """sitting and standing should not coexist."""
        tokens = ["sitting", "smile", "standing"]
        result = filter_conflicting_tokens(tokens)
        assert "sitting" in result
        assert "standing" not in result

    def test_lying_vs_others(self):
        """lying conflicts with sitting and standing."""
        tokens = ["lying", "sitting", "standing"]
        result = filter_conflicting_tokens(tokens)
        assert result == ["lying"]
