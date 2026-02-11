"""Tests for StyleContext value object and resolve/extract helpers."""

from unittest.mock import MagicMock, patch

from services.style_context import (
    StyleContext,
    _resolve_embedding_triggers,
    extract_style_loras,
    resolve_style_context,
    resolve_style_context_from_group,
)


class TestResolveEmbeddingTriggers:
    """Test _resolve_embedding_triggers delegation."""

    def test_empty_ids_returns_empty(self):
        assert _resolve_embedding_triggers(None, MagicMock()) == []
        assert _resolve_embedding_triggers([], MagicMock()) == []

    def test_resolves_trigger_words(self):
        emb = MagicMock()
        emb.trigger_word = "beautiful_style"
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [emb]

        result = _resolve_embedding_triggers([1], db)
        assert result == ["beautiful_style"]


class TestResolveStyleContext:
    """Test resolve_style_context from storyboard cascade."""

    def test_none_storyboard_returns_none(self):
        assert resolve_style_context(None, MagicMock()) is None

    @patch("services.config_resolver.resolve_effective_config")
    def test_full_cascade(self, mock_resolve):
        mock_resolve.return_value = {"values": {"style_profile_id": 1}, "sources": {}}
        db = MagicMock()

        storyboard = MagicMock()
        storyboard.group_id = 1
        group = MagicMock()
        profile = MagicMock()
        profile.id = 1
        profile.name = "anime_style"
        profile.loras = [{"lora_id": 10, "weight": 0.7}]
        profile.positive_embeddings = None
        profile.negative_embeddings = None
        profile.default_positive = "masterpiece"
        profile.default_negative = "lowres"
        lora_obj = MagicMock()
        lora_obj.name = "flat_color"
        lora_obj.trigger_words = ["flat_color"]

        def query_side(model):
            mock_q = MagicMock()
            name = getattr(model, "__name__", str(model))
            if name == "Storyboard":
                mock_q.filter.return_value.first.return_value = storyboard
            elif name == "Group":
                mock_q.options.return_value.filter.return_value.first.return_value = group
            elif name == "StyleProfile":
                mock_q.filter.return_value.first.return_value = profile
            elif name == "LoRA":
                mock_q.filter.return_value.first.return_value = lora_obj
            return mock_q

        db.query.side_effect = query_side

        ctx = resolve_style_context(5, db)
        assert ctx is not None
        assert ctx.profile_id == 1
        assert ctx.profile_name == "anime_style"
        assert len(ctx.loras) == 1
        assert ctx.loras[0]["name"] == "flat_color"
        assert ctx.default_positive == "masterpiece"
        assert ctx.default_negative == "lowres"

    def test_missing_storyboard_returns_none(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        assert resolve_style_context(999, db) is None


class TestResolveStyleContextFromGroup:
    """Test resolve_style_context_from_group."""

    @patch("services.config_resolver.resolve_effective_config")
    def test_resolves_from_group(self, mock_resolve):
        mock_resolve.return_value = {"values": {"style_profile_id": 2}, "sources": {}}
        db = MagicMock()

        group = MagicMock()
        profile = MagicMock()
        profile.id = 2
        profile.name = "cel_shade"
        profile.loras = []
        profile.positive_embeddings = None
        profile.negative_embeddings = None
        profile.default_positive = ""
        profile.default_negative = ""

        def query_side(model):
            mock_q = MagicMock()
            name = getattr(model, "__name__", str(model))
            if name == "Group":
                mock_q.options.return_value.filter.return_value.first.return_value = group
            elif name == "StyleProfile":
                mock_q.filter.return_value.first.return_value = profile
            return mock_q

        db.query.side_effect = query_side

        ctx = resolve_style_context_from_group(1, db)
        assert ctx is not None
        assert ctx.profile_id == 2

    def test_missing_group_returns_none(self):
        db = MagicMock()

        def query_side(model):
            mock_q = MagicMock()
            mock_q.options.return_value.filter.return_value.first.return_value = None
            return mock_q

        db.query.side_effect = query_side
        assert resolve_style_context_from_group(999, db) is None


class TestExtractStyleLoras:
    """Test extract_style_loras helper."""

    def test_none_context_returns_empty(self):
        assert extract_style_loras(None) == []

    def test_extracts_name_weight_triggers(self):
        ctx = StyleContext(
            profile_id=1,
            profile_name="test",
            loras=[
                {"lora_id": 1, "name": "flat_color", "weight": 0.7, "trigger_words": ["flat_color"]},
                {"lora_id": 2, "name": "anime", "weight": 0.5, "trigger_words": []},
            ],
        )
        result = extract_style_loras(ctx)
        assert len(result) == 2
        assert result[0] == {"name": "flat_color", "weight": 0.7, "trigger_words": ["flat_color"]}
        assert result[1] == {"name": "anime", "weight": 0.5, "trigger_words": []}

    def test_frozen_dataclass(self):
        import pytest

        ctx = StyleContext(profile_id=1, profile_name="test")
        with pytest.raises(AttributeError):
            ctx.profile_id = 2  # type: ignore
