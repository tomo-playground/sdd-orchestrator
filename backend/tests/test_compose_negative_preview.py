"""Unit tests for _compose_negative_preview() in routers/prompt.py."""

from unittest.mock import MagicMock, patch

from routers.prompt import _compose_negative_preview


def _make_style_ctx(default_negative="", negative_embeddings=None):
    ctx = MagicMock()
    ctx.default_negative = default_negative
    ctx.negative_embeddings = negative_embeddings or []
    return ctx


def _make_character(name, custom_negative="", recommended_negative=None):
    char = MagicMock()
    char.name = name
    char.custom_negative_prompt = custom_negative or None
    char.recommended_negative = recommended_negative
    return char


class TestComposeNegativePreviewStyleOnly:
    """StyleProfile negative sources only."""

    @patch("services.style_context.resolve_style_context")
    def test_style_default_negative(self, mock_ctx):
        mock_ctx.return_value = _make_style_ctx(default_negative="worst quality, low quality")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result, sources = _compose_negative_preview(
            storyboard_id=1,
            character_id=None,
            character_b_id=None,
            scene_negative="",
            db=db,
        )

        assert "worst quality" in result
        assert len(sources) == 1
        assert sources[0]["source"] == "style_profile"
        assert "worst_quality" in sources[0]["tokens"] or "worst quality" in sources[0]["tokens"]

    @patch("services.style_context.resolve_style_context")
    def test_style_with_embeddings(self, mock_ctx):
        mock_ctx.return_value = _make_style_ctx(
            default_negative="worst quality",
            negative_embeddings=["easynegative", "badhandv4"],
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result, sources = _compose_negative_preview(
            storyboard_id=1,
            character_id=None,
            character_b_id=None,
            scene_negative="",
            db=db,
        )

        assert "easynegative" in result
        assert "badhandv4" in result
        assert len(sources) == 1
        # Embeddings merged into style_profile source
        assert "easynegative" in sources[0]["tokens"]

    @patch("services.style_context.resolve_style_context")
    def test_style_dedup_within_source(self, mock_ctx):
        """default_negative and embeddings sharing same token should not duplicate."""
        mock_ctx.return_value = _make_style_ctx(
            default_negative="EasyNegative",
            negative_embeddings=["EasyNegative", "badhandv4"],
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result, sources = _compose_negative_preview(
            storyboard_id=1,
            character_id=None,
            character_b_id=None,
            scene_negative="",
            db=db,
        )

        assert len(sources) == 1
        easy_count = sources[0]["tokens"].count("EasyNegative")
        assert easy_count == 1, f"Expected 1 'EasyNegative' in tokens, got {easy_count}"
        assert "badhandv4" in sources[0]["tokens"]


class TestComposeNegativePreviewCharacterOnly:
    """Character negative sources only."""

    @patch("services.style_context.resolve_style_context", return_value=None)
    def test_character_custom_negative(self, _):
        char = _make_character("Miku", custom_negative="nsfw, revealing_clothes")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = char

        result, sources = _compose_negative_preview(
            storyboard_id=None,
            character_id=1,
            character_b_id=None,
            scene_negative="",
            db=db,
        )

        assert "nsfw" in result
        assert len(sources) == 1
        assert sources[0]["source"] == "character:Miku"

    @patch("services.style_context.resolve_style_context", return_value=None)
    def test_character_recommended_negative(self, _):
        char = _make_character("Miku", recommended_negative=["verybadimagenegative_v1.3"])
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = char

        result, sources = _compose_negative_preview(
            storyboard_id=None,
            character_id=1,
            character_b_id=None,
            scene_negative="",
            db=db,
        )

        assert "verybadimagenegative_v1.3" in result
        assert sources[0]["source"] == "character:Miku"


class TestComposeNegativePreviewCombined:
    """Combined sources: style + character + scene."""

    @patch("services.style_context.resolve_style_context")
    def test_all_sources_combined(self, mock_ctx):
        mock_ctx.return_value = _make_style_ctx(default_negative="worst quality")
        char = _make_character("Miku", custom_negative="nsfw")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = char

        result, sources = _compose_negative_preview(
            storyboard_id=1,
            character_id=1,
            character_b_id=None,
            scene_negative="blurry, text",
            db=db,
        )

        assert "worst quality" in result
        assert "nsfw" in result
        assert "blurry" in result
        assert len(sources) == 3
        source_names = [s["source"] for s in sources]
        assert "style_profile" in source_names
        assert "character:Miku" in source_names
        assert "scene" in source_names

    @patch("services.style_context.resolve_style_context")
    def test_deduplication(self, mock_ctx):
        """Duplicate tokens across sources should be deduplicated in final string."""
        mock_ctx.return_value = _make_style_ctx(default_negative="nsfw, worst quality")
        char = _make_character("Miku", custom_negative="nsfw")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = char

        result, sources = _compose_negative_preview(
            storyboard_id=1,
            character_id=1,
            character_b_id=None,
            scene_negative="",
            db=db,
        )

        # "nsfw" appears in both style and character, but final should deduplicate
        tokens = [t.strip() for t in result.split(",")]
        nsfw_count = tokens.count("nsfw")
        assert nsfw_count == 1, f"Expected 1 'nsfw', got {nsfw_count}"


class TestComposeNegativePreviewMultiChar:
    """Multi-character scene: both characters contribute."""

    @patch("services.style_context.resolve_style_context", return_value=None)
    def test_two_characters(self, _):
        char_a = _make_character("Miku", custom_negative="nsfw")
        char_b = _make_character("Rin", custom_negative="muscular, facial_hair")
        db = MagicMock()
        # Return different chars for sequential queries
        db.query.return_value.filter.return_value.first.side_effect = [
            char_a,
            char_b,
        ]

        result, sources = _compose_negative_preview(
            storyboard_id=None,
            character_id=1,
            character_b_id=2,
            scene_negative="",
            db=db,
        )

        assert "nsfw" in result
        assert "muscular" in result
        source_names = [s["source"] for s in sources]
        assert "character:Miku" in source_names
        assert "character:Rin" in source_names


class TestComposeNegativePreviewEmpty:
    """Edge case: no sources at all."""

    @patch("services.style_context.resolve_style_context", return_value=None)
    def test_empty_result(self, _):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result, sources = _compose_negative_preview(
            storyboard_id=None,
            character_id=None,
            character_b_id=None,
            scene_negative="",
            db=db,
        )

        assert result == ""
        assert sources == []
