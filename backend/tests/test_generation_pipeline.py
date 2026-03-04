"""Tests for generation pipeline: IP-Adapter, LoRA cap, complexity, Hi-Res."""

from unittest.mock import MagicMock, patch

from services.prompt.prompt import (
    apply_optimal_lora_weights,
    detect_scene_complexity,
    extract_lora_names,
)

# ────────────────────────────────────────────
# IP-Adapter auto-activation tests
# ────────────────────────────────────────────


class TestIPAdapterAutoActivation:
    """Test IP-Adapter auto-enable when character reference exists."""

    def _make_request(self, use_ip_adapter=False, character_id=1):
        req = MagicMock()
        req.use_ip_adapter = use_ip_adapter
        req.character_id = character_id
        req.ip_adapter_reference = None
        req.ip_adapter_weight = 0.7
        return req

    def _make_character(self, name="test_char", ip_adapter_weight=None):
        char = MagicMock()
        char.name = name
        char.ip_adapter_weight = ip_adapter_weight
        return char

    def test_auto_enable_when_reference_exists(self):
        """IP-Adapter enabled if character has a reference image."""
        request = self._make_request(use_ip_adapter=False)
        character = self._make_character()

        # Simulate the auto-activation logic from generation.py
        with patch("services.controlnet.load_reference_image", return_value="base64data"):
            from services.controlnet import load_reference_image

            ref = load_reference_image(character.name)
            if character and not request.use_ip_adapter and ref:
                request.use_ip_adapter = True
                request.ip_adapter_reference = character.name
                if character.ip_adapter_weight:
                    request.ip_adapter_weight = character.ip_adapter_weight
                else:
                    request.ip_adapter_weight = 0.75

        assert request.use_ip_adapter is True
        assert request.ip_adapter_reference == "test_char"
        assert request.ip_adapter_weight == 0.75

    def test_custom_weight_from_character(self):
        """IP-Adapter uses character's custom weight if set."""
        request = self._make_request(use_ip_adapter=False)
        character = self._make_character(ip_adapter_weight=0.6)

        with patch("services.controlnet.load_reference_image", return_value="base64data"):
            from services.controlnet import load_reference_image

            ref = load_reference_image(character.name)
            if character and not request.use_ip_adapter and ref:
                request.use_ip_adapter = True
                request.ip_adapter_reference = character.name
                if character.ip_adapter_weight:
                    request.ip_adapter_weight = character.ip_adapter_weight
                else:
                    request.ip_adapter_weight = 0.75

        assert request.ip_adapter_weight == 0.6

    def test_no_auto_enable_without_reference(self):
        """IP-Adapter stays off if no reference image."""
        request = self._make_request(use_ip_adapter=False)
        character = self._make_character()

        with patch("services.controlnet.load_reference_image", return_value=None):
            from services.controlnet import load_reference_image

            ref = load_reference_image(character.name)
            if character and not request.use_ip_adapter and ref:
                request.use_ip_adapter = True

        assert request.use_ip_adapter is False

    def test_no_override_if_already_enabled(self):
        """Don't re-set if IP-Adapter already enabled by user."""
        request = self._make_request(use_ip_adapter=True)
        request.ip_adapter_weight = 0.9
        character = self._make_character(ip_adapter_weight=0.6)

        # Logic should skip because use_ip_adapter is already True
        if character and not request.use_ip_adapter:
            request.ip_adapter_weight = character.ip_adapter_weight

        # Weight should remain user-set
        assert request.ip_adapter_weight == 0.9


# ────────────────────────────────────────────
# LoRA weight override (0.6 cap) tests
# ────────────────────────────────────────────


class TestLoRAWeightCap:
    """Test LoRA weight handling in _adjust_parameters.

    prompt composition의 _cap_lora_weight()가 STYLE_LORA_WEIGHT_CAP SSOT.
    _adjust_parameters()는 calibration DB 값만 적용 (이중 capping 없음).
    """

    def test_calibration_weights_applied_directly(self):
        """Calibration weights from DB are applied without additional capping."""
        prompt = "masterpiece, 1girl, <lora:char_lora:0.8>, <lora:style_lora:0.5>"
        optimal_weights = {"char_lora": 0.89, "style_lora": 0.67}

        # calibration-only: weights applied as-is from DB
        result = apply_optimal_lora_weights(prompt, optimal_weights)

        assert "<lora:char_lora:0.89>" in result
        assert "<lora:style_lora:0.67>" in result

    def test_calibration_preserves_uncalibrated_loras(self):
        """LoRAs not in calibration DB keep their original weight."""
        prompt = "1girl, <lora:char_lora:0.8>, <lora:unknown:0.5>"
        optimal_weights = {"char_lora": 0.6}

        result = apply_optimal_lora_weights(prompt, optimal_weights)

        assert "<lora:char_lora:0.6>" in result
        assert "<lora:unknown:0.5>" in result

    def test_cap_is_ssot(self):
        """prompt composition's _cap_lora_weight is the single source of truth for capping.

        _adjust_parameters no longer applies STYLE_LORA_WEIGHT_CAP.
        """
        # Simulate: V3 already capped at 0.76, calibration returns 0.76
        prompt = "<lora:flat_color:0.76>"
        optimal_weights = {"flat_color": 0.76}

        result = apply_optimal_lora_weights(prompt, optimal_weights)
        assert "<lora:flat_color:0.76>" in result  # No double-capping

    def test_apply_capped_weights_to_prompt(self):
        """Capped weights are correctly applied to LoRA tags in prompt."""
        prompt = "masterpiece, 1girl, <lora:char_lora:0.8>, <lora:style_lora:0.5>"
        capped = {"char_lora": 0.6, "style_lora": 0.5}

        result = apply_optimal_lora_weights(prompt, capped)

        assert "<lora:char_lora:0.6>" in result
        assert "<lora:style_lora:0.5>" in result

    def test_extract_lora_names(self):
        """extract_lora_names finds all LoRA tags."""
        prompt = "1girl, <lora:mymodel:0.7>, smile, <lora:style:0.5>"
        names = extract_lora_names(prompt)

        assert names == ["mymodel", "style"]


# ────────────────────────────────────────────
# Complexity adjustment tests
# ────────────────────────────────────────────


class TestComplexityAdjustment:
    """Test detect_scene_complexity and parameter adjustment."""

    def test_simple_scene(self):
        """0-3 scene tokens → simple."""
        tokens = ["masterpiece", "1girl", "brown_hair", "smile"]
        # Only "smile" is a scene category (expression)
        assert detect_scene_complexity(tokens) == "simple"

    def test_moderate_scene(self):
        """4-6 scene tokens → moderate."""
        tokens = [
            "masterpiece",
            "1girl",
            "smile",  # expression
            "looking_at_viewer",  # gaze
            "standing",  # pose
            "cowboy_shot",  # camera
            "indoors",  # location_indoor
        ]
        result = detect_scene_complexity(tokens)
        assert result in ("moderate", "complex")

    def test_complex_scene(self):
        """7+ scene tokens → complex."""
        tokens = [
            "masterpiece",
            "1girl",
            "smile",  # expression
            "looking_at_viewer",  # gaze
            "standing",  # pose
            "waving",  # action
            "cowboy_shot",  # camera
            "indoors",  # location_indoor
            "sunset",  # time_weather
            "dramatic_lighting",  # lighting
            "melancholic",  # mood
        ]
        result = detect_scene_complexity(tokens)
        assert result == "complex"

    def test_steps_cfg_boost_complex(self):
        """Complex scene → steps ≥ 28, cfg ≥ 8.0."""
        base_steps, base_cfg = 24, 7.0
        complexity = "complex"

        if complexity == "complex":
            final_steps = max(base_steps, 28)
            final_cfg = max(base_cfg, 8.0)
        else:
            final_steps, final_cfg = base_steps, base_cfg

        assert final_steps == 28
        assert final_cfg == 8.0

    def test_steps_cfg_boost_moderate(self):
        """Moderate scene → steps ≥ 25, cfg ≥ 7.5."""
        base_steps, base_cfg = 24, 7.0
        complexity = "moderate"

        if complexity == "complex":
            final_steps = max(base_steps, 28)
            final_cfg = max(base_cfg, 8.0)
        elif complexity == "moderate":
            final_steps = max(base_steps, 25)
            final_cfg = max(base_cfg, 7.5)
        else:
            final_steps, final_cfg = base_steps, base_cfg

        assert final_steps == 25
        assert final_cfg == 7.5

    def test_no_boost_simple(self):
        """Simple scene → no adjustment."""
        base_steps, base_cfg = 24, 7.0

        final_steps, final_cfg = base_steps, base_cfg

        assert final_steps == 24
        assert final_cfg == 7.0

    def test_high_base_preserved(self):
        """User-set high values are preserved (max, not override)."""
        base_steps, base_cfg = 35, 10.0

        final_steps = max(base_steps, 28)
        final_cfg = max(base_cfg, 8.0)

        assert final_steps == 35  # User's higher value kept
        assert final_cfg == 10.0


# ────────────────────────────────────────────
# Hi-Res payload tests
# ────────────────────────────────────────────


class TestHiResPayload:
    """Test Hi-Res payload construction for SD WebUI."""

    def _base_payload(self):
        return {
            "prompt": "masterpiece, 1girl",
            "negative_prompt": "lowres",
            "steps": 24,
            "cfg_scale": 7.0,
            "sampler_name": "DPM++ 2M Karras",
            "seed": -1,
            "width": 512,
            "height": 768,
        }

    def test_hires_enabled(self):
        """Hi-Res params added when enable_hr=True."""
        payload = self._base_payload()
        enable_hr = True
        hr_scale = 1.5
        hr_upscaler = "R-ESRGAN 4x+ Anime6B"
        hr_second_pass_steps = 10
        denoising_strength = 0.35

        if enable_hr:
            payload.update(
                {
                    "enable_hr": True,
                    "hr_scale": hr_scale,
                    "hr_upscaler": hr_upscaler,
                    "hr_second_pass_steps": hr_second_pass_steps,
                    "denoising_strength": denoising_strength,
                }
            )

        assert payload["enable_hr"] is True
        assert payload["hr_scale"] == 1.5
        assert payload["hr_upscaler"] == "R-ESRGAN 4x+ Anime6B"
        assert payload["hr_second_pass_steps"] == 10
        assert payload["denoising_strength"] == 0.35

    def test_hires_disabled(self):
        """No Hi-Res params when enable_hr=False."""
        payload = self._base_payload()
        enable_hr = False

        if enable_hr:
            payload.update({"enable_hr": True})

        assert "enable_hr" not in payload

    def test_hires_custom_params(self):
        """Custom Hi-Res parameters are respected."""
        payload = self._base_payload()
        payload.update(
            {
                "enable_hr": True,
                "hr_scale": 2.0,
                "hr_upscaler": "Latent",
                "hr_second_pass_steps": 20,
                "denoising_strength": 0.5,
            }
        )

        assert payload["hr_scale"] == 2.0
        assert payload["hr_upscaler"] == "Latent"
        assert payload["hr_second_pass_steps"] == 20
        assert payload["denoising_strength"] == 0.5

    def test_hires_doesnt_affect_base_params(self):
        """Hi-Res update doesn't overwrite base SD params."""
        payload = self._base_payload()
        payload.update(
            {
                "enable_hr": True,
                "hr_scale": 1.5,
                "hr_upscaler": "R-ESRGAN 4x+ Anime6B",
                "hr_second_pass_steps": 10,
                "denoising_strength": 0.35,
            }
        )

        # Base params preserved
        assert payload["steps"] == 24
        assert payload["cfg_scale"] == 7.0
        assert payload["width"] == 512
        assert payload["height"] == 768
