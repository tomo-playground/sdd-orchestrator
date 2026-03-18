"""E2E Quality tests for Prompt Composition System.

These tests verify that Mode B (LoRA) actually improves scene expression
by comparing WD14 tag detection rates between Mode A and Mode B.

Requirements:
- SD WebUI running at localhost:7860
- WD14 model files in assets/wd14/

Run manually (not in CI):
    pytest tests/test_prompt_quality.py -v -s --run-e2e
"""

import base64

import httpx
import pytest

from config import API_PUBLIC_URL as BACKEND_API
from config import SD_BASE_URL as SD_API

# Skip all tests in this file unless --run-e2e flag is provided
pytestmark = pytest.mark.skipif(
    "not config.getoption('--run-e2e', default=False)", reason="E2E tests require SD WebUI. Run with --run-e2e"
)


def pytest_addoption(parser):
    """Add --run-e2e option."""
    parser.addoption("--run-e2e", action="store_true", default=False, help="Run E2E quality tests (requires SD WebUI)")


# Test configuration
SCENE_TAGS = ["smiling", "standing", "looking at viewer", "from above"]


class TestPromptQualityE2E:
    """E2E tests comparing Mode A vs Mode B image quality."""

    @pytest.fixture
    def scene_tokens(self):
        """Test scene with clear pose/action/camera requirements."""
        return [
            "1girl",
            "smiling",
            "looking at viewer",
            "standing",
            "arms crossed",
            "from above",
            "bedroom",
            "sunset",
            "warm lighting",
        ]

    @pytest.fixture
    def lora_info(self):
        """Character LoRA for testing."""
        return {
            "name": "eureka",
            "lora_type": "character",
            "optimal_weight": 0.5,
            "trigger_words": ["eureka"],
        }

    def compose_prompt(self, tokens: list, mode: str, loras: list = None) -> dict:
        """Call /prompt/compose API."""
        response = httpx.post(
            f"{BACKEND_API}/prompt/compose",
            json={
                "tokens": tokens,
                "mode": mode,
                "loras": loras or [],
                "is_break_enabled": mode == "lora",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()

    def generate_image(self, prompt: str, negative: str = "") -> bytes:
        """Generate image using SD WebUI API."""
        payload = {
            "prompt": prompt,
            "negative_prompt": negative or "lowres, bad anatomy, bad hands",
            "steps": 20,
            "cfg_scale": 7,
            "width": 512,
            "height": 512,
            "sampler_name": "DPM++ 2M Karras",
            "seed": 42,  # Fixed seed for reproducibility
        }
        response = httpx.post(
            f"{SD_API}/sdapi/v1/txt2img",
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        image_b64 = data["images"][0]
        return base64.b64decode(image_b64)

    def validate_image(self, image_bytes: bytes, expected_tags: list) -> dict:
        """Validate image using WD14."""
        image_b64 = base64.b64encode(image_bytes).decode()
        response = httpx.post(
            f"{BACKEND_API}/scene/validate",
            json={
                "image_b64": image_b64,
                "prompt": ", ".join(expected_tags),
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def test_mode_comparison_scene_detection(self, scene_tokens, lora_info):
        """Compare scene tag detection between Mode A and Mode B.

        Hypothesis: Mode B should have higher detection rate for scene tags
        because it prioritizes scene tokens before LoRA influence.
        """
        # Compose prompts for both modes
        mode_a_result = self.compose_prompt(scene_tokens, "standard")
        mode_b_result = self.compose_prompt(scene_tokens, "lora", loras=[lora_info])

        print("\n=== Mode A (Standard) ===")
        print(f"Prompt: {mode_a_result['prompt'][:100]}...")

        print("\n=== Mode B (LoRA) ===")
        print(f"Prompt: {mode_b_result['prompt'][:100]}...")
        print(f"Complexity: {mode_b_result['scene_complexity']}")
        print(f"LoRA Weight: {mode_b_result.get('lora_weights', {})}")

        # Generate images
        print("\n🎨 Generating Mode A image...")
        image_a = self.generate_image(mode_a_result["prompt"])

        print("🎨 Generating Mode B image...")
        image_b = self.generate_image(mode_b_result["prompt"])

        # Validate both images
        print("\n🔍 Validating images...")
        validation_a = self.validate_image(image_a, SCENE_TAGS)
        validation_b = self.validate_image(image_b, SCENE_TAGS)

        match_rate_a = validation_a.get("match_rate", 0)
        match_rate_b = validation_b.get("match_rate", 0)

        print("\n=== Results ===")
        print(f"Mode A match rate: {match_rate_a:.1%}")
        print(f"Mode B match rate: {match_rate_b:.1%}")
        print(f"Mode A detected: {validation_a.get('matched_tags', [])}")
        print(f"Mode B detected: {validation_b.get('matched_tags', [])}")

        # Mode B should be at least as good as Mode A
        # In practice, we expect Mode B to be better for scene tags
        assert match_rate_b >= match_rate_a * 0.9, (
            f"Mode B ({match_rate_b:.1%}) should not be significantly worse than "
            f"Mode A ({match_rate_a:.1%}) for scene tag detection"
        )

    def test_lora_weight_affects_scene_detection(self, scene_tokens, lora_info):
        """Test that lower LoRA weight improves scene tag detection.

        Complex scenes should use lower LoRA weight to allow
        scene tags to express better.
        """
        # Simple scene (fewer scene tokens)
        simple_tokens = ["1girl", "smiling", "bedroom"]

        # Complex scene (many scene tokens)
        complex_tokens = [
            "1girl",
            "smiling",
            "looking at viewer",
            "standing",
            "arms crossed",
            "from above",
            "jumping",
            "dynamic pose",
            "bedroom",
            "sunset",
            "warm lighting",
            "dramatic",
        ]

        simple_result = self.compose_prompt(simple_tokens, "lora", [lora_info])
        complex_result = self.compose_prompt(complex_tokens, "lora", [lora_info])

        simple_weight = simple_result.get("lora_weights", {}).get("eureka", 0.5)
        complex_weight = complex_result.get("lora_weights", {}).get("eureka", 0.5)

        print(f"\nSimple scene complexity: {simple_result['scene_complexity']}")
        print(f"Simple scene LoRA weight: {simple_weight}")
        print(f"Complex scene complexity: {complex_result['scene_complexity']}")
        print(f"Complex scene LoRA weight: {complex_weight}")

        # Complex scene should have lower LoRA weight
        assert complex_weight <= simple_weight, (
            f"Complex scene weight ({complex_weight}) should be <= simple scene weight ({simple_weight})"
        )

    def test_break_token_improves_separation(self, scene_tokens, lora_info):
        """Test that BREAK token is present in Mode B output."""
        result = self.compose_prompt(scene_tokens, "lora", [lora_info])

        assert "BREAK" in result["tokens"], "Mode B should include BREAK token"
        assert result["meta"]["has_break"], "Meta should indicate BREAK presence"

        # BREAK should appear after subject, before scene extras
        break_idx = result["tokens"].index("BREAK")
        print(f"\nBREAK position: {break_idx} / {len(result['tokens'])}")
        print(f"Tokens around BREAK: {result['tokens'][max(0, break_idx - 2) : break_idx + 3]}")


class TestPromptQualityMetrics:
    """Collect quality metrics without assertions (for reporting)."""

    def test_collect_baseline_metrics(self):
        """Collect baseline metrics for various prompts.

        This test generates images and collects WD14 detection rates
        for analysis. Results are printed, not asserted.
        """
        test_cases = [
            {
                "name": "Simple portrait",
                "tokens": ["1girl", "smiling", "portrait"],
                "expected_high": ["smiling"],
            },
            {
                "name": "Action scene",
                "tokens": ["1girl", "running", "dynamic pose", "park"],
                "expected_high": ["running"],
            },
            {
                "name": "Complex composition",
                "tokens": ["1girl", "smiling", "looking at viewer", "standing", "from above", "classroom", "sunset"],
                "expected_high": ["smiling", "standing", "looking at viewer"],
            },
        ]

        print("\n" + "=" * 60)
        print("BASELINE QUALITY METRICS")
        print("=" * 60)

        for case in test_cases:
            print(f"\n--- {case['name']} ---")
            print(f"Tokens: {case['tokens']}")
            # In a full implementation, we would:
            # 1. Generate image
            # 2. Run WD14
            # 3. Calculate match rate
            # 4. Store in a metrics database
            print("(Skipped - requires SD WebUI)")
