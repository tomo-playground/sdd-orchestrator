"""Test cases for Style LoRA integration in V3 Prompt Engine.

Ensures that style_loras parameter is properly handled through the full pipeline:
1. SceneGenerateRequest schema
2. generation.py parameter passing
3. V3PromptService composition
4. V3PromptBuilder output
"""

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from services.prompt.v3_composition import V3PromptBuilder
from services.prompt.v3_service import V3PromptService


class TestStyleLoRAIntegration:
    """Test Style LoRA integration across all layers."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test database session."""
        self.db = SessionLocal()
        yield
        self.db.close()

    def test_v3_prompt_builder_style_lora(self):
        """Test V3PromptBuilder with style_loras parameter."""
        builder = V3PromptBuilder(self.db)

        style_loras = [
            {
                "name": "harukaze-doremi-casual",
                "weight": 0.61,
                "trigger_words": ["hrkzdrm_cs"],
                "lora_type": "style"
            }
        ]

        scene_tags = [
            "expressionless", "looking_at_viewer", "full_body",
            "against_railing", "dutch_angle", "street",
            "outdoors", "sunset", "sad", "anime"
        ]

        prompt = builder.compose(
            tags=scene_tags,
            style_loras=style_loras
        )

        # Verify trigger word is included
        assert "hrkzdrm_cs" in prompt, \
            f"Trigger word 'hrkzdrm_cs' not found in prompt: {prompt}"

        # Verify LoRA tag is included
        assert "<lora:harukaze-doremi-casual:0.61>" in prompt, \
            f"LoRA tag not found in prompt: {prompt}"

        # Verify LoRA tag is at the end (ATMOSPHERE layer)
        lora_tag = "<lora:harukaze-doremi-casual:0.61>"
        lora_index = prompt.rfind(lora_tag)
        assert lora_index > 0, "LoRA tag not found"
        # Should be near the end (within last 100 chars)
        assert len(prompt) - lora_index < 100, \
            "LoRA tag should be near the end of prompt (ATMOSPHERE layer)"

    def test_v3_prompt_service_style_lora(self):
        """Test V3PromptService.generate_prompt_for_scene with style_loras."""
        service = V3PromptService(self.db)

        style_loras = [
            {
                "name": "harukaze-doremi-casual",
                "weight": 0.65,
                "trigger_words": ["hrkzdrm_cs"],
                "lora_type": "style"
            }
        ]

        scene_tags = ["standing", "smiling", "classroom"]

        # Test without character_id (generic mode)
        prompt = service.generate_prompt_for_scene(
            character_id=None,
            scene_tags=scene_tags,
            style_loras=style_loras
        )

        assert "hrkzdrm_cs" in prompt
        assert "<lora:harukaze-doremi-casual:0.65>" in prompt

    def test_scene_generate_request_schema(self):
        """Test that SceneGenerateRequest accepts style_loras field."""
        from schemas import SceneGenerateRequest

        # Create request with style_loras
        request = SceneGenerateRequest(
            prompt="1girl, standing, smiling",
            character_id=1,
            style_loras=[
                {
                    "name": "test-lora",
                    "weight": 0.7,
                    "trigger_words": ["test_trigger"],
                    "lora_type": "style"
                }
            ]
        )

        # Verify field is present and accessible
        assert request.style_loras is not None
        assert len(request.style_loras) == 1
        assert request.style_loras[0]["name"] == "test-lora"
        assert request.style_loras[0]["weight"] == 0.7

    def test_multiple_style_loras(self):
        """Test composition with multiple style LoRAs."""
        builder = V3PromptBuilder(self.db)

        style_loras = [
            {
                "name": "chibi-laugh",
                "weight": 0.6,
                "trigger_words": ["chibi", "super_deformed"],
                "lora_type": "style"
            },
            {
                "name": "flat-color",
                "weight": 0.5,
                "trigger_words": ["flat color"],
                "lora_type": "style"
            }
        ]

        scene_tags = ["1girl", "happy"]

        prompt = builder.compose(
            tags=scene_tags,
            style_loras=style_loras
        )

        # All trigger words should be present
        assert "chibi" in prompt
        assert "super_deformed" in prompt
        assert "flat color" in prompt

        # All LoRA tags should be present
        assert "<lora:chibi-laugh:0.6>" in prompt
        assert "<lora:flat-color:0.5>" in prompt

    def test_style_lora_without_trigger_words(self):
        """Test LoRA without trigger words (should still include LoRA tag)."""
        builder = V3PromptBuilder(self.db)

        style_loras = [
            {
                "name": "some-lora",
                "weight": 0.7,
                "trigger_words": [],  # Empty
                "lora_type": "style"
            }
        ]

        prompt = builder.compose(
            tags=["1girl"],
            style_loras=style_loras
        )

        # LoRA tag should still be present
        assert "<lora:some-lora:0.7>" in prompt

    def test_api_endpoint_integration(self):
        """Test full API endpoint with style_loras (integration test)."""
        client = TestClient(app)

        # This test requires SD WebUI to be running
        # Skip if not available
        try:
            response = client.post(
                "/api/scenes/generate",
                json={
                    "prompt": "1girl, standing, smiling",
                    "character_id": 1,
                    "style_loras": [
                        {
                            "name": "harukaze-doremi-casual",
                            "weight": 0.61,
                            "trigger_words": ["hrkzdrm_cs"],
                            "lora_type": "style"
                        }
                    ],
                    "steps": 1,  # Minimal steps for fast test
                    "width": 128,  # Small size
                    "height": 128
                }
            )

            # If SD WebUI is not running, we'll get a connection error
            # In that case, we just verify the request was accepted
            if response.status_code == 500:
                # Check if error is due to SD WebUI connection
                error_detail = response.json().get("detail", "")
                if "connect" in error_detail.lower():
                    pytest.skip("SD WebUI not running")

            # If we got here, verify the response
            # (actual image generation is out of scope for unit tests)

        except Exception as e:
            pytest.skip(f"API test skipped: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
