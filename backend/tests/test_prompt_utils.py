"""Tests for prompt utility SSOT: split_prompt_tokens is the single source."""

from services.prompt.prompt import split_prompt_tokens


class TestSplitPromptTokensIsSSoT:
    """split_prompt_tokens() must be the only split implementation."""

    def test_basic_split(self):
        result = split_prompt_tokens("1girl, smile, blue_eyes")
        assert result == ["1girl", "smile", "blue_eyes"]

    def test_empty_string(self):
        assert split_prompt_tokens("") == []

    def test_whitespace_handling(self):
        result = split_prompt_tokens("  tag1 ,  tag2  ,  ")
        assert result == ["tag1", "tag2"]

    def test_single_token(self):
        assert split_prompt_tokens("solo") == ["solo"]


class TestImageGenerationCoreUsesSharedSplit:
    """image_generation_core must delegate to split_prompt_tokens, not re-implement."""

    def test_no_private_split_function(self):
        """_split_prompt_tokens should not exist in image_generation_core."""
        import services.image_generation_core as mod

        assert not hasattr(mod, "_split_prompt_tokens"), (
            "image_generation_core still has _split_prompt_tokens — should use "
            "split_prompt_tokens from services.prompt.prompt"
        )
