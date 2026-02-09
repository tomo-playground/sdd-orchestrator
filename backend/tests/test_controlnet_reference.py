"""Tests for controlnet.py generate_reference_for_character.

BLOCKER #2: Tags must keep underscore format (Danbooru standard).
WARNING #7: Must use config constants for SD params.
"""

import inspect


class TestTagFormatInReference:
    """generate_reference_for_character must not convert underscores to spaces."""

    def test_no_replace_underscore_to_space_in_source(self):
        """Source code must not contain tag.name.replace('_', ' ')."""
        import services.controlnet as mod

        source = inspect.getsource(mod.generate_reference_for_character)
        assert '.replace("_", " ")' not in source, (
            "generate_reference_for_character still converts underscores to spaces"
        )
        assert ".replace('_', ' ')" not in source, (
            "generate_reference_for_character still converts underscores to spaces"
        )


class TestConfigConstantsUsage:
    """generate_reference_for_character must use config constants."""

    def test_uses_sd_txt2img_url_constant(self):
        """Must reference SD_TXT2IMG_URL from config, not hardcode URL."""
        import services.controlnet as mod

        source = inspect.getsource(mod.generate_reference_for_character)
        assert "SD_TXT2IMG_URL" in source, "generate_reference_for_character should use SD_TXT2IMG_URL from config"


class TestIntentionalBypassComment:
    """Reference generation is intentionally separate from generate_image_with_v3."""

    def test_has_intentional_bypass_comment(self):
        """Must have INTENTIONAL BYPASS comment documenting the reason."""
        import services.controlnet as mod

        source = inspect.getsource(mod.generate_reference_for_character)
        assert "INTENTIONAL BYPASS" in source, "generate_reference_for_character needs INTENTIONAL BYPASS comment"
