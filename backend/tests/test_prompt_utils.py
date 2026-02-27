"""Tests for prompt utility SSOT: split_prompt_tokens is the single source."""

from services.prompt.prompt import merge_tags_dedup, split_prompt_tokens


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


class TestMergeTagsDedup:
    """merge_tags_dedup: BG 태그 등 중복 없이 병합."""

    def test_basic_merge(self):
        result = merge_tags_dedup(["cafe", "indoors"], ["table", "chair"])
        assert result == ["cafe", "indoors", "table", "chair"]

    def test_dedup_exact(self):
        result = merge_tags_dedup(["cafe", "indoors"], ["cafe", "table"])
        assert result == ["cafe", "indoors", "table"]

    def test_dedup_case_insensitive(self):
        result = merge_tags_dedup(["Cafe"], ["cafe"])
        assert result == ["Cafe"]

    def test_dedup_space_underscore(self):
        result = merge_tags_dedup(["brown_hair"], ["brown hair"])
        assert result == ["brown_hair"]

    def test_empty_extra(self):
        base = ["a", "b"]
        result = merge_tags_dedup(base, [])
        assert result == ["a", "b"]

    def test_does_not_mutate_base(self):
        base = ["a"]
        merge_tags_dedup(base, ["b"])
        assert base == ["a"]


class TestImageGenerationCoreUsesSharedSplit:
    """image_generation_core must delegate to split_prompt_tokens, not re-implement."""

    def test_no_private_split_function(self):
        """_split_prompt_tokens should not exist in image_generation_core."""
        import services.image_generation_core as mod

        assert not hasattr(mod, "_split_prompt_tokens"), (
            "image_generation_core still has _split_prompt_tokens — should use "
            "split_prompt_tokens from services.prompt.prompt"
        )
