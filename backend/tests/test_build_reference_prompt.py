"""Tests for build_reference_prompt() — reference image prompt construction.

Covers:
- LoRA trigger word injection (regression: trigger words were missing → flat_color LoRA ineffective)
- Weight stripping from character tags
- Lower-body/abstract tag removal for upper_body framing
- looking_away vs looking_at_viewer conflict resolution
"""

from dataclasses import dataclass, field

import pytest

from config_prompt import REFERENCE_UPPER_BODY_REMOVE_TAGS  # noqa: E402
from services.characters.reference import build_reference_prompt


@dataclass(frozen=True)
class FakeStyleContext:
    """Minimal StyleContext stub for testing."""

    loras: list[dict] = field(default_factory=list)


class TestTriggerWordInjection:
    """LoRA trigger words MUST appear in the final prompt."""

    def test_style_lora_trigger_injected(self):
        """Regression: flat_color trigger was missing → LoRA had no effect."""
        ctx = FakeStyleContext(
            loras=[
                {"name": "flat_color_v2", "weight": 0.6, "trigger_words": ["flat color"]},
            ]
        )
        result = build_reference_prompt("1girl, blonde_hair", ctx)
        assert "<lora:flat_color_v2:0.6>" in result
        assert "flat color" in result or "flat_color" in result

    def test_multiple_loras_all_triggers(self):
        ctx = FakeStyleContext(
            loras=[
                {"name": "flat_color_v2", "weight": 0.6, "trigger_words": ["flat color"]},
                {"name": "detailer_v1", "weight": 0.35, "trigger_words": []},
            ]
        )
        result = build_reference_prompt("1girl", ctx)
        assert "<lora:flat_color_v2:0.6>" in result
        assert "<lora:detailer_v1:0.35>" in result
        assert "flat color" in result

    def test_no_trigger_when_empty(self):
        ctx = FakeStyleContext(loras=[{"name": "detailer_v1", "weight": 0.35, "trigger_words": []}])
        result = build_reference_prompt("1girl", ctx)
        assert "<lora:detailer_v1:0.35>" in result
        # No extra tokens beyond LoRA tag
        after_lora = result.split("<lora:detailer_v1:0.35>")[1]
        assert after_lora.strip().strip(",").strip() == ""

    def test_no_trigger_when_none(self):
        ctx = FakeStyleContext(loras=[{"name": "style_lora", "weight": 0.5}])
        result = build_reference_prompt("1girl", ctx)
        assert "<lora:style_lora:0.5>" in result

    def test_weight_capped_at_style_lora_weight_cap(self):
        """LoRA weight > STYLE_LORA_WEIGHT_CAP (0.76) must be clamped."""
        ctx = FakeStyleContext(loras=[{"name": "heavy_lora", "weight": 0.9, "trigger_words": []}])
        result = build_reference_prompt("1girl", ctx)
        assert "<lora:heavy_lora:0.76>" in result
        assert "<lora:heavy_lora:0.9>" not in result

    def test_whitespace_trigger_skipped(self):
        ctx = FakeStyleContext(loras=[{"name": "lora_x", "weight": 0.5, "trigger_words": ["", "  ", "valid_trigger"]}])
        result = build_reference_prompt("1girl", ctx)
        assert "valid_trigger" in result

    def test_no_style_ctx(self):
        result = build_reference_prompt("1girl, blonde_hair", None)
        assert "1girl" in result
        assert "<lora:" not in result


class TestWeightStripping:
    """Weight emphasis (tag:1.3) must be stripped for ComfyUI reference."""

    def test_weight_stripped(self):
        result = build_reference_prompt("(blonde_hair:1.3), (blue_eyes:1.2)", None)
        assert "blonde_hair" in result
        assert "blue_eyes" in result
        assert ":1.3" not in result
        assert ":1.2" not in result

    def test_plain_tags_preserved(self):
        result = build_reference_prompt("1girl, blonde_hair", None)
        assert "1girl" in result
        assert "blonde_hair" in result


class TestRemoveTags:
    """Lower-body and abstract tags must be removed for upper_body framing."""

    @pytest.mark.parametrize("tag", sorted(REFERENCE_UPPER_BODY_REMOVE_TAGS))
    def test_removed_tags(self, tag):
        result = build_reference_prompt(f"1girl, {tag}, blonde_hair", None)
        tokens = [t.strip() for t in result.split(",")]
        assert tag not in tokens

    def test_identity_tags_kept(self):
        result = build_reference_prompt("1girl, blonde_hair, blue_eyes, white_blouse", None)
        assert "blonde_hair" in result
        assert "blue_eyes" in result
        assert "white_blouse" in result


class TestGazeConflict:
    """looking_away in character prompt must suppress looking_at_viewer default."""

    def test_default_looking_at_viewer(self):
        result = build_reference_prompt("1girl, blonde_hair", None)
        assert "looking_at_viewer" in result

    def test_looking_away_overrides(self):
        result = build_reference_prompt("1girl, looking_away", None)
        assert "looking_away" in result
        assert "looking_at_viewer" not in result


class TestPromptStructure:
    """Final prompt must follow expected structure."""

    def test_base_structure(self):
        result = build_reference_prompt("1girl, blonde_hair", None)
        assert result.startswith("masterpiece, best_quality,")
        assert "solo" in result
        assert "upper_body" in result
        assert "simple_background" in result

    def test_empty_positive_prompt(self):
        result = build_reference_prompt(None, None)
        assert "masterpiece" in result
        assert "solo" in result
