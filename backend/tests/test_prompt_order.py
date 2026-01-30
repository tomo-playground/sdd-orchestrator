"""Test prompt composition order and LoRA inclusion.

Tests the fundamental requirements:
1. Quality tags come first
2. LoRA tags are included in output
3. Trigger words are included
4. Token order follows spec (quality → LoRA → character → scene)
"""

from __future__ import annotations

from services.prompt.prompt_composition import compose_prompt_tokens


class TestPromptOrder:
    """Test prompt token ordering."""

    def test_quality_tags_first(self):
        """Quality tags should appear first in prompt."""
        tokens = ["smiling", "park", "masterpiece", "best_quality"]
        result = compose_prompt_tokens(tokens, mode="standard")

        # Find indices of quality tags
        masterpiece_idx = next((i for i, t in enumerate(result) if "masterpiece" in t.lower()), -1)
        best_quality_idx = next((i for i, t in enumerate(result) if "best_quality" in t.lower()), -1)

        # Quality tags should be at the beginning
        assert masterpiece_idx >= 0, "masterpiece should be in result"
        assert best_quality_idx >= 0, "best_quality should be in result"
        assert masterpiece_idx < 3, f"masterpiece should be in first 3 positions, got {masterpiece_idx}"
        assert best_quality_idx < 3, f"best_quality should be in first 3 positions, got {best_quality_idx}"

    def test_lora_included_in_output(self):
        """LoRA tags must be included in composed prompt."""
        tokens = ["smiling", "park", "red_hair"]
        lora_strings = ["<lora:harukaze-doremi-casual:0.61>"]

        result = compose_prompt_tokens(
            tokens,
            mode="lora",
            lora_strings=lora_strings,
        )

        # LoRA must be in output
        lora_found = any("<lora:" in t for t in result)
        assert lora_found, f"LoRA not found in result: {result}"

        # Check specific LoRA
        assert "<lora:harukaze-doremi-casual:0.61>" in result, f"Specific LoRA missing: {result}"

    def test_trigger_words_included(self):
        """Trigger words must be included in composed prompt."""
        tokens = ["smiling", "park", "hrkzdrm_cs"]
        trigger_words = ["hrkzdrm_cs"]

        result = compose_prompt_tokens(
            tokens,
            mode="standard",
            trigger_words=trigger_words,
        )

        # Trigger word must be in output
        assert "hrkzdrm_cs" in result, f"Trigger word missing: {result}"

    def test_lora_mode_order(self):
        """Test complete prompt order in LoRA mode.

        Expected order:
        1. Quality tags (masterpiece, best_quality)
        2. LoRA tags
        3. Trigger words
        4. Character features (hair, etc.)
        5. Actions/expressions
        6. Scene/location
        """
        tokens = [
            "double_bun",
            "red_hair",
            "hrkzdrm_cs",
            "(smile:1.2)",
            "(looking_at_viewer:1.2)",
            "(standing:1.2)",
            "full_body",
            "park",
            "day",
            "sun",
            "adjusting_hair",
            "cute_anime_style",
        ]
        lora_strings = ["<lora:harukaze-doremi-casual:0.61>"]
        trigger_words = ["hrkzdrm_cs"]

        result = compose_prompt_tokens(
            tokens,
            mode="lora",
            lora_strings=lora_strings,
            trigger_words=trigger_words,
            use_break=False,  # Simplify test
        )

        # Convert to string for easier analysis
        result_str = ", ".join(result)
        print(f"\n[DEBUG] Composed prompt:\n{result_str}\n")

        # 1. Quality tags should be first
        masterpiece_idx = next((i for i, t in enumerate(result) if "masterpiece" in t.lower()), -1)
        best_quality_idx = next((i for i, t in enumerate(result) if "best_quality" in t.lower()), -1)
        assert masterpiece_idx >= 0, "masterpiece missing"
        assert best_quality_idx >= 0, "best_quality missing"
        assert max(masterpiece_idx, best_quality_idx) < 3, "Quality tags should be in first 3 positions"

        # 2. LoRA should come early (before most character features)
        lora_idx = next((i for i, t in enumerate(result) if "<lora:" in t), -1)
        assert lora_idx >= 0, "LoRA missing from result"
        assert lora_idx < 10, f"LoRA too late in prompt (position {lora_idx})"

        # 3. Trigger word should be near LoRA
        trigger_idx = next((i for i, t in enumerate(result) if "hrkzdrm_cs" in t), -1)
        assert trigger_idx >= 0, "Trigger word missing"
        assert abs(trigger_idx - lora_idx) < 5, f"Trigger word too far from LoRA (trigger: {trigger_idx}, lora: {lora_idx})"

        # 4. Character features should come before scene
        red_hair_idx = next((i for i, t in enumerate(result) if "red_hair" in t), -1)
        park_idx = next((i for i, t in enumerate(result) if "park" in t.lower()), -1)
        if red_hair_idx >= 0 and park_idx >= 0:
            assert red_hair_idx < park_idx, f"Character features should come before scene (hair: {red_hair_idx}, park: {park_idx})"

    def test_user_prompt_with_lora_embedded(self):
        """Test handling of prompt that already contains LoRA tags."""
        # User input: includes LoRA in token list
        tokens = [
            "double_bun",
            "red_hair",
            "hrkzdrm_cs",
            "<lora:harukaze-doremi-casual:0.61>",  # User included LoRA in prompt
            "(smile:1.2)",
            "park",
        ]

        result = compose_prompt_tokens(
            tokens,
            mode="lora",
            lora_strings=None,  # No separate LoRA list
            trigger_words=["hrkzdrm_cs"],
        )

        # LoRA should still be in output (extracted and re-inserted)
        lora_found = any("<lora:" in t for t in result)
        assert lora_found, f"LoRA not preserved from user input: {result}"

    def test_no_duplicate_loras(self):
        """Test that duplicate LoRAs are removed."""
        tokens = []
        lora_strings = [
            "<lora:test:0.5>",
            "<lora:test:0.6>",  # Duplicate (should keep last weight)
            "<lora:other:0.7>",
        ]

        result = compose_prompt_tokens(
            tokens,
            mode="lora",
            lora_strings=lora_strings,
        )

        # Count LoRA tags
        lora_count = sum(1 for t in result if t.startswith("<lora:test:"))
        assert lora_count == 1, f"Expected 1 LoRA, got {lora_count}: {result}"

        # Should keep last weight
        assert "<lora:test:0.6>" in result, f"Should keep last LoRA weight: {result}"
        assert "<lora:test:0.5>" not in result, f"Should remove earlier LoRA: {result}"


class TestPromptOrderRealWorld:
    """Test with real-world example from user report."""

    def test_doremi_scenario(self):
        """Test exact scenario from user report.

        User reported:
        - Input has LoRA and trigger words
        - Output missing LoRA and character features
        """
        # Input from user's JSON
        tokens = [
            "double_bun",
            "red_hair",
            "hrkzdrm_cs",
            "(smile:1.2)",
            "(looking_at_viewer:1.2)",
            "(standing:1.2)",
            "full_body",
            "park",
            "day",
            "sun",
            "masterpiece",
            "best_quality",
            "adjusting_hair",
            "cute_anime_style",
        ]
        lora_strings = ["<lora:harukaze-doremi-casual:0.61>"]
        trigger_words = ["hrkzdrm_cs"]

        result = compose_prompt_tokens(
            tokens,
            mode="lora",
            lora_strings=lora_strings,
            trigger_words=trigger_words,
        )

        result_str = ", ".join(result)
        print(f"\n[DOREMI TEST] Composed prompt:\n{result_str}\n")

        # Critical assertions
        assert any("<lora:" in t for t in result), "❌ LoRA missing (reported bug)"
        assert any("hrkzdrm_cs" in t for t in result), "❌ Trigger word missing (reported bug)"
        assert any("double_bun" in t for t in result), "❌ Character feature missing (reported bug)"
        assert any("red_hair" in t for t in result), "❌ Character feature missing (reported bug)"

        # Order assertions
        masterpiece_idx = next((i for i, t in enumerate(result) if "masterpiece" in t.lower()), -1)
        lora_idx = next((i for i, t in enumerate(result) if "<lora:" in t), -1)
        smile_idx = next((i for i, t in enumerate(result) if "smile" in t.lower()), -1)

        assert masterpiece_idx < lora_idx, "Quality should come before LoRA"
        assert lora_idx < smile_idx, "LoRA should come before actions"

        print("✅ All assertions passed")
        print(f"   masterpiece: {masterpiece_idx}, LoRA: {lora_idx}, smile: {smile_idx}")
