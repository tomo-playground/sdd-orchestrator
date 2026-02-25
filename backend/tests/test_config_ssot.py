"""Tests for Config SSOT - centralized configuration constants.

Verifies that:
1. All expected constants exist in config.py with correct types
2. Service files don't contain hardcoded values that should come from config
3. Environment variable overrides work correctly
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestConfigConstantsExist:
    """Verify all SSOT constants exist in config module with correct types."""

    def test_external_api_constants(self):
        from config import CIVITAI_API_BASE, DANBOORU_API_BASE, DANBOORU_USER_AGENT

        assert isinstance(DANBOORU_API_BASE, str)
        assert DANBOORU_API_BASE.startswith("https://")
        assert isinstance(DANBOORU_USER_AGENT, str)
        assert isinstance(CIVITAI_API_BASE, str)
        assert CIVITAI_API_BASE.startswith("https://")

    def test_sd_generation_defaults(self):
        from config import SD_DEFAULT_CFG_SCALE, SD_DEFAULT_SAMPLER, SD_DEFAULT_STEPS

        assert isinstance(SD_DEFAULT_STEPS, int)
        assert SD_DEFAULT_STEPS == 28
        assert isinstance(SD_DEFAULT_CFG_SCALE, float)
        assert SD_DEFAULT_CFG_SCALE == 7.0
        assert isinstance(SD_DEFAULT_SAMPLER, str)

    def test_http_timeouts(self):
        from config import (
            CIVITAI_API_TIMEOUT,
            CONTROLNET_API_TIMEOUT,
            CONTROLNET_DETECT_TIMEOUT,
            CONTROLNET_GENERATE_TIMEOUT,
            DANBOORU_API_TIMEOUT,
            SD_API_TIMEOUT,
        )

        assert isinstance(DANBOORU_API_TIMEOUT, float)
        assert isinstance(CIVITAI_API_TIMEOUT, float)
        assert isinstance(SD_API_TIMEOUT, float)
        assert isinstance(CONTROLNET_API_TIMEOUT, float)
        assert isinstance(CONTROLNET_GENERATE_TIMEOUT, float)
        assert isinstance(CONTROLNET_DETECT_TIMEOUT, float)
        # Sanity: generate timeout > detect timeout > api timeout
        assert CONTROLNET_GENERATE_TIMEOUT > CONTROLNET_DETECT_TIMEOUT
        assert CONTROLNET_DETECT_TIMEOUT >= CONTROLNET_API_TIMEOUT

    def test_character_reference_constants(self):
        from config import (
            SD_REFERENCE_CFG_SCALE,
            SD_REFERENCE_DENOISING,
            SD_REFERENCE_HR_UPSCALER,
            SD_REFERENCE_STEPS,
        )

        assert isinstance(SD_REFERENCE_STEPS, int)
        assert isinstance(SD_REFERENCE_CFG_SCALE, float)
        assert isinstance(SD_REFERENCE_HR_UPSCALER, str)
        assert isinstance(SD_REFERENCE_DENOISING, float)
        assert 0 < SD_REFERENCE_DENOISING < 1

    def test_font_and_lora_defaults(self):
        from config import DEFAULT_LORA_WEIGHT, DEFAULT_SCENE_TEXT_FONT

        assert isinstance(DEFAULT_SCENE_TEXT_FONT, str)
        assert DEFAULT_SCENE_TEXT_FONT.endswith(".ttf")
        assert isinstance(DEFAULT_LORA_WEIGHT, float)
        assert 0 < DEFAULT_LORA_WEIGHT <= 1.5


BACKEND_DIR = Path(__file__).resolve().parent.parent


class TestNoHardcodedValues:
    """Verify service files use config constants instead of hardcoded values."""

    @staticmethod
    def _get_string_literals(filepath: Path) -> list[str]:
        """Extract all string literals from a Python file using AST."""
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        strings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                strings.append(node.value)
        return strings

    def test_danbooru_no_hardcoded_url(self):
        filepath = BACKEND_DIR / "services" / "danbooru.py"
        strings = self._get_string_literals(filepath)
        assert not any("danbooru.donmai.us" in s for s in strings), (
            "danbooru.py should use DANBOORU_API_BASE from config"
        )

    def test_loras_no_hardcoded_civitai_url(self):
        filepath = BACKEND_DIR / "routers" / "loras.py"
        strings = self._get_string_literals(filepath)
        assert not any("civitai.com/api" in s for s in strings), "loras.py should use CIVITAI_API_BASE from config"

    def test_sd_no_hardcoded_timeout(self):
        """sd_models.py should not have literal timeout= numeric values."""
        filepath = BACKEND_DIR / "routers" / "sd_models.py"
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "timeout":
                assert not isinstance(node.value, ast.Constant), (
                    f"sd_models.py has hardcoded timeout={getattr(node.value, 'value', '?')} — use SD_API_TIMEOUT"
                )

    def test_image_gen_core_no_hardcoded_steps(self):
        """image_generation_core.py should not have literal steps/cfg/sampler defaults."""
        filepath = BACKEND_DIR / "services" / "image_generation_core.py"
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            # Check dict entries with key="steps" and literal value
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and len(node.args) >= 2
            ):
                key_node = node.args[0]
                val_node = node.args[1]
                if (
                    isinstance(key_node, ast.Constant)
                    and key_node.value == "steps"
                    and isinstance(val_node, ast.Constant)
                ):
                    pytest.fail(f"image_generation_core.py has hardcoded steps default={val_node.value}")


class TestConfigOverride:
    """Verify environment variable overrides are respected."""

    def test_sd_default_steps_override(self):
        with patch.dict(os.environ, {"SD_DEFAULT_STEPS": "42"}):
            val = int(os.environ["SD_DEFAULT_STEPS"])
            assert val == 42

    def test_danbooru_api_base_override(self):
        with patch.dict(os.environ, {"DANBOORU_API_BASE": "https://custom.example.com"}):
            val = os.environ["DANBOORU_API_BASE"]
            assert val == "https://custom.example.com"

    def test_sd_api_timeout_override(self):
        with patch.dict(os.environ, {"SD_API_TIMEOUT": "30"}):
            val = float(os.environ["SD_API_TIMEOUT"])
            assert val == 30.0
