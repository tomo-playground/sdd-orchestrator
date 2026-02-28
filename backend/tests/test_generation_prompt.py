"""Tests for prompt routing, context_tags merging, and skip_loras parameter."""

import logging
from unittest.mock import MagicMock, patch

from schemas import SceneGenerateRequest
from services.generation_context import GenerationContext
from services.generation_prompt import (
    _collect_context_tags,
    _merge_context_tags,
    _resolve_style_loras,
    apply_style_profile_to_prompt,
)
from services.generation_prompt import prepare_prompt as _prepare_prompt


def _make_request(**overrides) -> SceneGenerateRequest:
    defaults = {"prompt": "1girl, standing", "character_id": 1, "storyboard_id": 10}
    defaults.update(overrides)
    return SceneGenerateRequest(**defaults)


def _make_character(name="test_char", **kw):
    char = MagicMock()
    char.name = name
    char.id = kw.get("id", 1)
    char.ip_adapter_weight = kw.get("ip_adapter_weight", None)
    char.ip_adapter_model = kw.get("ip_adapter_model", None)
    return char


def _call_prepare(req, db):
    """Helper: wrap _prepare_prompt with GenerationContext."""
    ctx = GenerationContext(request=req)
    _prepare_prompt(req, db, ctx)
    return ctx.prompt, ctx.warnings, ctx.character, ctx.consistency


# ────────────────────────────────────────────
# context_tags collection and merging
# ────────────────────────────────────────────


class TestCollectContextTags:
    """Test _collect_context_tags flattening."""

    def test_flattens_list_fields(self):
        tags = _collect_context_tags(
            {
                "expression": ["smile", "open_mouth"],
                "pose": ["standing"],
                "action": ["waving"],
                "environment": ["outdoors"],
                "mood": ["happy"],
            }
        )
        assert tags == ["smile", "open_mouth", "standing", "waving", "outdoors", "happy"]

    def test_flattens_string_fields(self):
        tags = _collect_context_tags({"gaze": "looking_at_viewer", "camera": "cowboy_shot"})
        assert tags == ["looking_at_viewer", "cowboy_shot"]

    def test_empty_dict(self):
        assert _collect_context_tags({}) == []

    def test_mixed_fields(self):
        tags = _collect_context_tags(
            {
                "expression": ["smile"],
                "gaze": "looking_at_viewer",
                "camera": "",
            }
        )
        assert tags == ["smile", "looking_at_viewer"]

    def test_none_values_ignored(self):
        tags = _collect_context_tags({"expression": None, "gaze": None})
        assert tags == []


class TestMergeContextTags:
    """Test _merge_context_tags prepending to request.prompt."""

    def test_merges_tags_into_prompt(self):
        req = _make_request(
            prompt="1girl, standing",
            context_tags={"expression": ["smile"], "gaze": "looking_at_viewer"},
        )
        _merge_context_tags(req)
        assert req.prompt.startswith("smile, looking_at_viewer, ")
        assert "1girl, standing" in req.prompt

    def test_no_context_tags_no_change(self):
        req = _make_request(prompt="1girl, standing", context_tags=None)
        _merge_context_tags(req)
        assert req.prompt == "1girl, standing"

    def test_empty_context_tags_no_change(self):
        req = _make_request(prompt="1girl, standing", context_tags={})
        _merge_context_tags(req)
        assert req.prompt == "1girl, standing"


class TestContextTagsInPipeline:
    """Test context_tags are merged during _handle_character_scene."""

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras", return_value=[])
    def test_context_tags_merged_into_character_scene(self, mock_resolve, mock_ref):
        """context_tags are prepended to prompt before V3 composition."""
        req = _make_request(
            prompt="1girl, standing",
            context_tags={"expression": ["smile"], "camera": "cowboy_shot"},
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("composed", "bad", [])
            _call_prepare(req, db)

        call_kwargs = mock_compose.call_args.kwargs
        # context_tags should be merged into raw_prompt
        assert "smile" in call_kwargs["raw_prompt"]
        assert "cowboy_shot" in call_kwargs["raw_prompt"]
        assert "1girl" in call_kwargs["raw_prompt"]

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras", return_value=[])
    def test_context_tags_merged_into_background_scene(self, mock_resolve, mock_ref):
        """context_tags are prepended in narrator background scenes too."""
        req = _make_request(
            character_id=None,
            prompt="no_humans, bedroom",
            context_tags={"environment": ["night"], "mood": ["dark"]},
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("composed", "bad", [])
            _call_prepare(req, db)

        call_kwargs = mock_compose.call_args.kwargs
        assert "night" in call_kwargs["raw_prompt"]
        assert "dark" in call_kwargs["raw_prompt"]

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras", return_value=[])
    def test_no_context_tags_prompt_unchanged(self, mock_resolve, mock_ref):
        """Without context_tags, prompt passes through unchanged."""
        req = _make_request(prompt="1girl, standing", context_tags=None)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("composed", "bad", [])
            _call_prepare(req, db)

        call_kwargs = mock_compose.call_args.kwargs
        assert call_kwargs["raw_prompt"] == "1girl, standing"


# ────────────────────────────────────────────
# prompt_pre_composed flag routing (DEPRECATED)
# ────────────────────────────────────────────


class TestPreparePromptFlag:
    """Test prompt_pre_composed flag behavior in _prepare_prompt."""

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt.apply_style_profile_to_prompt")
    def test_pre_composed_with_lora_skips_injection(self, mock_style, mock_ref):
        """prompt_pre_composed=True + LoRA already present → skip_loras=True."""
        prompt_with_lora = "masterpiece, 1girl, standing, <lora:J_huiben:0.8>, J_huiben"
        mock_style.return_value = (prompt_with_lora, "bad")
        req = _make_request(prompt_pre_composed=True, prompt=prompt_with_lora)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            cleaned, warnings, char, _strategy = _call_prepare(req, db)

        mock_compose.assert_not_called()
        mock_style.assert_called_once()
        call_kwargs = mock_style.call_args
        assert call_kwargs.kwargs.get("skip_loras", False) is True

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras")
    @patch("services.generation_prompt.apply_style_profile_to_prompt")
    def test_pre_composed_without_lora_injects_from_db(self, mock_style, mock_resolve, mock_ref):
        """prompt_pre_composed=True + no LoRA in prompt → resolves from DB and injects."""
        # apply_style_profile returns prompt WITHOUT LoRA (skip_loras=False but profile has none)
        mock_style.return_value = ("masterpiece, 1girl, standing", "bad")
        mock_resolve.return_value = [{"name": "J_huiben", "weight": 0.8, "trigger_words": ["J_huiben"]}]
        req = _make_request(prompt_pre_composed=True, prompt="masterpiece, 1girl, standing")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            cleaned, warnings, char, _strategy = _call_prepare(req, db)

        mock_compose.assert_not_called()
        # Safety net: LoRA injected from DB
        assert "<lora:J_huiben:0.8>" in cleaned
        assert "J_huiben" in cleaned

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras")
    @patch("services.generation_prompt.apply_style_profile_to_prompt")
    def test_pre_composed_no_storyboard_no_injection(self, mock_style, mock_resolve, mock_ref):
        """prompt_pre_composed=True + no storyboard_id → no safety-net injection."""
        mock_style.return_value = ("masterpiece, 1girl, standing", "bad")
        req = _make_request(prompt_pre_composed=True, prompt="masterpiece, 1girl, standing", storyboard_id=None)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        cleaned, warnings, char, _strategy = _call_prepare(req, db)

        mock_resolve.assert_not_called()
        assert "<lora:" not in cleaned

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras", return_value=[])
    def test_raw_prompt_runs_v3(self, mock_resolve, mock_ref):
        """prompt_pre_composed=False + character → compose_scene_with_style called."""
        req = _make_request(prompt_pre_composed=False)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("v3_composed", "bad", [])
            cleaned, warnings, char, _strategy = _call_prepare(req, db)

        mock_compose.assert_called_once()
        call_kwargs = mock_compose.call_args.kwargs
        assert call_kwargs["character_id"] == 1
        assert call_kwargs["storyboard_id"] == 10
        assert cleaned == "v3_composed"

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras", return_value=[])
    def test_scene_id_passed_to_compose(self, mock_resolve, mock_ref):
        """scene_id from request must be forwarded to compose_scene_with_style."""
        req = _make_request(prompt_pre_composed=False, scene_id=42)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("composed", "neg", [])
            _call_prepare(req, db)

        call_kwargs = mock_compose.call_args.kwargs
        assert call_kwargs["scene_id"] == 42

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras", return_value=[])
    def test_scene_id_none_by_default(self, mock_resolve, mock_ref):
        """No scene_id → scene_id=None passed to compose_scene_with_style."""
        req = _make_request(prompt_pre_composed=False)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("composed", "neg", [])
            _call_prepare(req, db)

        call_kwargs = mock_compose.call_args.kwargs
        assert call_kwargs["scene_id"] is None

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt.apply_style_profile_to_prompt")
    def test_no_character_applies_full_style_profile(self, mock_style, mock_ref):
        """No character_id → full style profile applied, V3 not called."""
        mock_style.return_value = ("quality, scenery, sunset", "bad")
        req = _make_request(character_id=None)
        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = None

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            cleaned, warnings, char, _strategy = _call_prepare(req, db)

        mock_compose.assert_not_called()
        mock_style.assert_called_once()
        assert char is None
        call_kwargs = mock_style.call_args
        assert call_kwargs.kwargs.get("skip_loras", False) is False


# ────────────────────────────────────────────
# skip_loras parameter
# ────────────────────────────────────────────


class TestStyleProfileSkipLoras:
    """Test skip_loras parameter in apply_style_profile_to_prompt."""

    def _mock_db(
        self,
        profile_loras=None,
        default_positive="masterpiece",
        default_negative="lowres",
        positive_embeddings=None,
        negative_embeddings=None,
        embedding_objs=None,
    ):
        db = MagicMock()
        storyboard = MagicMock()
        storyboard.group_id = 1

        group = MagicMock()
        group.project = MagicMock()

        profile = MagicMock()
        profile.name = "test_style"
        profile.id = 1
        profile.loras = profile_loras
        profile.default_positive = default_positive
        profile.default_negative = default_negative
        profile.positive_embeddings = positive_embeddings
        profile.negative_embeddings = negative_embeddings

        lora_obj = MagicMock()
        lora_obj.name = "flat_color"
        lora_obj.trigger_words = ["flat_color"]

        def query_side_effect(model):
            mock_q = MagicMock()
            model_name = getattr(model, "__name__", str(model))
            if model_name == "Storyboard":
                mock_q.filter.return_value.first.return_value = storyboard
            elif model_name == "Group":
                mock_q.options.return_value.filter.return_value.first.return_value = group
            elif model_name == "StyleProfile":
                mock_q.filter.return_value.first.return_value = profile
            elif model_name == "LoRA":
                mock_q.filter.return_value.first.return_value = lora_obj
            elif model_name == "Embedding":
                mock_q.filter.return_value.all.return_value = embedding_objs or []
            return mock_q

        db.query.side_effect = query_side_effect
        return db

    @patch("services.config_resolver.resolve_effective_config")
    def test_skip_loras_true_excludes_lora_tags(self, mock_resolve):
        mock_resolve.return_value = {"values": {"style_profile_id": 1}, "sources": {}}
        # Real JSONB: only lora_id + weight (no name)
        loras = [{"lora_id": 1, "weight": 0.7}]
        db = self._mock_db(profile_loras=loras)

        result_prompt, result_neg = apply_style_profile_to_prompt("1girl, standing", "bad", 10, db, skip_loras=True)

        assert "<lora:flat_color" not in result_prompt
        assert "flat_color" not in result_prompt.split(", ")  # trigger word excluded
        assert "masterpiece" in result_prompt  # quality preserved
        assert "lowres" in result_neg  # negative preserved

    @patch("services.config_resolver.resolve_effective_config")
    def test_skip_loras_true_keeps_quality_and_negative(self, mock_resolve):
        mock_resolve.return_value = {"values": {"style_profile_id": 1}, "sources": {}}
        loras = [{"lora_id": 1, "weight": 0.7}]
        db = self._mock_db(profile_loras=loras)

        result_prompt, result_neg = apply_style_profile_to_prompt("1girl", "", 10, db, skip_loras=True)

        assert "masterpiece" in result_prompt
        assert "lowres" in result_neg

    @patch("services.config_resolver.resolve_effective_config")
    def test_skip_loras_false_includes_everything(self, mock_resolve):
        mock_resolve.return_value = {"values": {"style_profile_id": 1}, "sources": {}}
        # Real JSONB: only lora_id + weight (name resolved from LoRA object)
        loras = [{"lora_id": 1, "weight": 0.7}]
        db = self._mock_db(profile_loras=loras)

        result_prompt, result_neg = apply_style_profile_to_prompt("1girl", "", 10, db, skip_loras=False)

        assert "<lora:flat_color:0.7>" in result_prompt
        assert "flat_color" in result_prompt  # trigger word included
        assert "masterpiece" in result_prompt

    @patch("services.config_resolver.resolve_effective_config")
    def test_default_positive_dedup_no_duplicates(self, mock_resolve):
        """Quality tags already in prompt are NOT duplicated by default_positive."""
        mock_resolve.return_value = {"values": {"style_profile_id": 1}, "sources": {}}
        db = self._mock_db(default_positive="masterpiece, best_quality")

        # Prompt already contains the same quality tags (from V3 /prompt/compose)
        result_prompt, _ = apply_style_profile_to_prompt("masterpiece, best_quality, 1girl, standing", "", 10, db)

        # Each quality tag should appear exactly once
        tokens = [t.strip() for t in result_prompt.split(",")]
        assert tokens.count("masterpiece") == 1
        assert tokens.count("best_quality") == 1
        assert "1girl" in tokens

    @patch("services.config_resolver.resolve_effective_config")
    def test_default_positive_dedup_partial_overlap(self, mock_resolve):
        """Only overlapping tokens are skipped; non-overlapping ones are added."""
        mock_resolve.return_value = {"values": {"style_profile_id": 1}, "sources": {}}
        db = self._mock_db(default_positive="masterpiece, best_quality, absurdres")

        # Prompt has masterpiece but not best_quality or absurdres
        result_prompt, _ = apply_style_profile_to_prompt("masterpiece, 1girl", "", 10, db)

        tokens = [t.strip() for t in result_prompt.split(",")]
        assert tokens.count("masterpiece") == 1
        assert "best_quality" in tokens
        assert "absurdres" in tokens

    @patch("services.config_resolver.resolve_effective_config")
    def test_embeddings_injected_into_prompts(self, mock_resolve):
        """Positive/negative embedding trigger words are injected."""
        mock_resolve.return_value = {"values": {"style_profile_id": 1}, "sources": {}}
        neg_emb = MagicMock()
        neg_emb.trigger_word = "EasyNegative"
        pos_emb = MagicMock()
        pos_emb.trigger_word = "beautiful_style"
        db = self._mock_db(
            positive_embeddings=[1],
            negative_embeddings=[2],
            embedding_objs=[neg_emb, pos_emb],
        )
        # Embedding query returns different results per call
        emb_call_count = {"n": 0}
        original_side = db.query.side_effect

        def patched_query(model):
            model_name = getattr(model, "__name__", str(model))
            if model_name == "Embedding":
                mock_q = MagicMock()
                emb_call_count["n"] += 1
                if emb_call_count["n"] == 1:
                    mock_q.filter.return_value.all.return_value = [pos_emb]
                else:
                    mock_q.filter.return_value.all.return_value = [neg_emb]
                return mock_q
            return original_side(model)

        db.query.side_effect = patched_query

        result_prompt, result_neg = apply_style_profile_to_prompt("1girl", "bad", 10, db)

        assert "beautiful_style" in result_prompt
        assert "EasyNegative" in result_neg

    @patch("services.config_resolver.resolve_effective_config")
    def test_embeddings_applied_even_with_skip_loras(self, mock_resolve):
        """Embeddings are applied regardless of skip_loras flag."""
        mock_resolve.return_value = {"values": {"style_profile_id": 1}, "sources": {}}
        neg_emb = MagicMock()
        neg_emb.trigger_word = "EasyNegative"
        db = self._mock_db(negative_embeddings=[1])

        def patched_query(model):
            mock_q = MagicMock()
            model_name = getattr(model, "__name__", str(model))
            if model_name == "Embedding":
                mock_q.filter.return_value.all.return_value = [neg_emb]
            elif model_name == "Storyboard":
                mock_q.filter.return_value.first.return_value = MagicMock(group_id=1)
            elif model_name == "Group":
                mock_q.options.return_value.filter.return_value.first.return_value = MagicMock()
            elif model_name == "StyleProfile":
                profile = MagicMock()
                profile.name = "test"
                profile.id = 1
                profile.loras = None
                profile.default_positive = "masterpiece"
                profile.default_negative = None
                profile.positive_embeddings = None
                profile.negative_embeddings = [1]
                mock_q.filter.return_value.first.return_value = profile
            return mock_q

        db.query.side_effect = patched_query

        result_prompt, result_neg = apply_style_profile_to_prompt("1girl", "", 10, db, skip_loras=True)

        assert "EasyNegative" in result_neg  # Embedding applied even with skip_loras

    @patch("services.config_resolver.resolve_effective_config")
    def test_lora_dedup_skips_existing_lora_in_prompt(self, mock_resolve):
        """Defense-in-depth: if prompt already has <lora:X>, skip_loras=False does not add it again."""
        mock_resolve.return_value = {"values": {"style_profile_id": 1}, "sources": {}}
        loras = [{"lora_id": 1, "weight": 0.7}]
        db = self._mock_db(profile_loras=loras)

        # Prompt already contains flat_color LoRA (from V3 composition)
        prompt_with_lora = "1girl, flat_color, <lora:flat_color:0.76>"
        result_prompt, _ = apply_style_profile_to_prompt(prompt_with_lora, "", 10, db, skip_loras=False)

        import re

        lora_tags = re.findall(r"<lora:flat_color:[^>]+>", result_prompt)
        assert len(lora_tags) == 1, f"Expected 1 LoRA tag, got {len(lora_tags)}: {lora_tags}"


# ────────────────────────────────────────────
# _resolve_style_loras
# ────────────────────────────────────────────


class TestResolveStyleLoras:
    """Test _resolve_style_loras fallback."""

    def test_returns_empty_without_storyboard(self):
        db = MagicMock()
        result = _resolve_style_loras(None, db)
        assert result == []

    @patch("services.config_resolver.resolve_effective_config")
    def test_resolves_from_storyboard_cascade(self, mock_resolve):
        """DB cascade resolves LoRA name + trigger_words from lora_id."""
        mock_resolve.return_value = {"values": {"style_profile_id": 1}, "sources": {}}
        db = MagicMock()

        storyboard = MagicMock()
        storyboard.group_id = 1
        group = MagicMock()
        profile = MagicMock()
        # Real JSONB: only lora_id + weight (no name)
        profile.loras = [{"lora_id": 1, "weight": 0.7}]
        lora_obj = MagicMock()
        lora_obj.name = "flat_color"
        lora_obj.trigger_words = ["flat_color"]

        def query_side_effect(model):
            mock_q = MagicMock()
            model_name = getattr(model, "__name__", str(model))
            if model_name == "Storyboard":
                mock_q.filter.return_value.first.return_value = storyboard
            elif model_name == "Group":
                mock_q.options.return_value.filter.return_value.first.return_value = group
            elif model_name == "StyleProfile":
                mock_q.filter.return_value.first.return_value = profile
            elif model_name == "LoRA":
                mock_q.filter.return_value.first.return_value = lora_obj
            return mock_q

        db.query.side_effect = query_side_effect

        result = _resolve_style_loras(10, db)
        assert len(result) == 1
        assert result[0]["name"] == "flat_color"
        assert result[0]["weight"] == 0.7
        assert result[0]["trigger_words"] == ["flat_color"]


# ────────────────────────────────────────────
# Batch LoRA resolution regression
# ────────────────────────────────────────────


class TestBatchLoraResolution:
    """Regression: batch path must resolve style_loras from DB, not frontend format."""

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras")
    def test_batch_ignores_frontend_style_loras(self, mock_resolve, mock_ref):
        """Even when frontend sends style_loras, DB resolution is used (SSOT)."""
        db_loras = [{"name": "flat_color", "weight": 0.7, "trigger_words": ["flat color"]}]
        mock_resolve.return_value = db_loras
        req = _make_request(
            prompt_pre_composed=False,
            style_loras=[{"lora_id": 5, "weight": 0.7}],
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("composed", "bad", [])
            _call_prepare(req, db)

        # compose_scene_with_style must receive DB-resolved loras (with name)
        call_kwargs = mock_compose.call_args.kwargs
        assert call_kwargs["style_loras"] == db_loras
        assert call_kwargs["style_loras"][0]["name"] == "flat_color"

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras")
    def test_batch_uses_db_even_with_empty_frontend_loras(self, mock_resolve, mock_ref):
        """DB resolution is always used regardless of frontend style_loras."""
        db_loras = [{"name": "flat_color", "weight": 0.7, "trigger_words": ["flat color"]}]
        mock_resolve.return_value = db_loras
        req = _make_request(prompt_pre_composed=False, style_loras=[])
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("composed", "bad", [])
            _call_prepare(req, db)

        mock_resolve.assert_called_once()
        call_kwargs = mock_compose.call_args.kwargs
        assert len(call_kwargs["style_loras"]) == 1
        assert call_kwargs["style_loras"][0]["name"] == "flat_color"


# ────────────────────────────────────────────
# Narrator background scene filtering
# ────────────────────────────────────────────


class TestNarratorBackgroundFiltering:
    """Test Narrator (no_humans) scenes route through compose_scene_with_style."""

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras", return_value=[])
    def test_narrator_no_humans_uses_compose_scene(self, mock_resolve, mock_ref):
        """no_humans + character_id=None → compose_scene_with_style called."""
        req = _make_request(character_id=None, prompt="no_humans, bedroom, night, full_body, standing")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("no_humans, bedroom, night", "bad", [])
            cleaned, _, _, _strategy = _call_prepare(req, db)

        mock_compose.assert_called_once()
        call_kwargs = mock_compose.call_args.kwargs
        assert call_kwargs["character_id"] is None
        assert cleaned == "no_humans, bedroom, night"

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras", return_value=[])
    def test_narrator_filters_character_tags(self, mock_resolve, mock_ref):
        """compose_scene_with_style strips character tags from no_humans scenes."""
        req = _make_request(character_id=None, prompt="no_humans, bedroom, full_body, standing")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("no_humans, bedroom", "bad", [])
            cleaned, _, _, _strategy = _call_prepare(req, db)

        assert "full_body" not in cleaned
        assert "standing" not in cleaned

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras", return_value=[])
    def test_narrator_preserves_environment_tags(self, mock_resolve, mock_ref):
        """Environment tags (bedroom, night) preserved through compose_scene_with_style."""
        req = _make_request(character_id=None, prompt="no_humans, bedroom, night")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("no_humans, bedroom, night", "bad", [])
            cleaned, _, _, _strategy = _call_prepare(req, db)

        assert "bedroom" in cleaned
        assert "night" in cleaned
        assert "no_humans" in cleaned

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt._resolve_style_loras")
    def test_narrator_applies_style_loras(self, mock_resolve, mock_ref):
        """style_loras are passed to compose_scene_with_style for Narrator scenes."""
        style_loras = [{"name": "flat_color", "weight": 0.7, "trigger_words": ["flat color"]}]
        mock_resolve.return_value = style_loras
        req = _make_request(character_id=None, prompt="no_humans, bedroom")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("no_humans, bedroom, <lora:flat_color:0.7>", "bad", [])
            _call_prepare(req, db)

        call_kwargs = mock_compose.call_args.kwargs
        assert call_kwargs["style_loras"] == style_loras

    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt.apply_style_profile_to_prompt")
    def test_no_character_with_person_tags_uses_style_profile(self, mock_style, mock_ref):
        """No character_id but person tags (1girl) → style profile only, no no_humans."""
        mock_style.return_value = ("1girl, standing, cafe", "bad")
        req = _make_request(character_id=None, prompt="1girl, standing, cafe")
        db = MagicMock()
        db.query.return_value.options.return_value.filter.return_value.first.return_value = None

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            cleaned, _, char, _strategy = _call_prepare(req, db)

        mock_compose.assert_not_called()
        assert char is None
        assert "no_humans" not in req.prompt

    @patch("services.generation_prompt._resolve_style_loras")
    @patch("services.character_consistency.load_reference_image", return_value=None)
    @patch("services.generation_prompt.apply_style_profile_to_prompt")
    def test_no_character_no_person_tags_injects_no_humans(self, mock_style, mock_ref, mock_resolve):
        """No character_id + no person tags → auto-inject no_humans, use V3 background."""
        mock_resolve.return_value = []
        req = _make_request(character_id=None, prompt="scenery, sunset, mountain")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("services.generation_prompt.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("no_humans, scenery, sunset, mountain", "bad", [])
            cleaned, _, char, _strategy = _call_prepare(req, db)

        # no_humans auto-injected → V3 background composition called
        mock_compose.assert_called_once()
        assert "no_humans" in req.prompt


# ────────────────────────────────────────────
# Safe Tags replacement (_apply_safe_tag_replacement)
# ────────────────────────────────────────────


class TestSafeTagReplacement:
    """Test _apply_safe_tag_replacement post-processing."""

    @patch("services.generation_prompt.TagAliasCache")
    def test_replaces_risky_tag(self, mock_cache_cls):
        from services.generation_prompt import _apply_safe_tag_replacement

        mock_cache_cls.get_replacement.side_effect = lambda t: ("cowboy_shot" if t == "medium_shot" else ...)
        result = _apply_safe_tag_replacement("1girl, medium_shot, standing", MagicMock())
        assert "cowboy_shot" in result
        assert "medium_shot" not in result

    @patch("services.generation_prompt.TagAliasCache")
    def test_preserves_lora_tags(self, mock_cache_cls):
        from services.generation_prompt import _apply_safe_tag_replacement

        mock_cache_cls.get_replacement.return_value = ...
        result = _apply_safe_tag_replacement("1girl, <lora:test:0.8>, standing", MagicMock())
        assert "<lora:test:0.8>" in result

    @patch("services.generation_prompt.TagAliasCache")
    def test_removes_null_mapped_tag(self, mock_cache_cls):
        from services.generation_prompt import _apply_safe_tag_replacement

        mock_cache_cls.get_replacement.side_effect = lambda t: (None if t == "bad_tag" else ...)
        result = _apply_safe_tag_replacement("1girl, bad_tag, standing", MagicMock())
        assert "bad_tag" not in result
        assert "1girl" in result
        assert "standing" in result

    @patch("services.generation_prompt.TagAliasCache")
    def test_idempotent(self, mock_cache_cls):
        from services.generation_prompt import _apply_safe_tag_replacement

        mock_cache_cls.get_replacement.return_value = ...
        prompt = "1girl, cowboy_shot, standing"
        result = _apply_safe_tag_replacement(prompt, MagicMock())
        assert result == prompt


# ────────────────────────────────────────────
# Auto Rewrite (_apply_auto_rewrite)
# ────────────────────────────────────────────


class TestAutoRewrite:
    """Test _apply_auto_rewrite post-processing."""

    @patch("services.generation_prompt.rewrite_prompt")
    def test_calls_gemini_and_returns_rewritten(self, mock_rewrite):
        from services.generation_prompt import _apply_auto_rewrite

        mock_rewrite.return_value = {"prompt": "improved, 1girl, standing, park"}
        result = _apply_auto_rewrite("1girl, standing")
        assert result == "improved, 1girl, standing, park"
        mock_rewrite.assert_called_once()

    @patch("services.generation_prompt.rewrite_prompt")
    def test_fallback_on_error(self, mock_rewrite):
        from services.generation_prompt import _apply_auto_rewrite

        mock_rewrite.side_effect = Exception("Gemini unavailable")
        result = _apply_auto_rewrite("1girl, standing")
        assert result == "1girl, standing"

    @patch("services.generation_prompt.rewrite_prompt")
    def test_preserves_lora_tokens_after_rewrite(self, mock_rewrite):
        from services.generation_prompt import _apply_auto_rewrite

        # Gemini returns rewritten prompt WITHOUT LoRA
        mock_rewrite.return_value = {"prompt": "improved, 1girl, park"}
        result = _apply_auto_rewrite("1girl, <lora:test:0.8>, standing")
        assert "<lora:test:0.8>" in result
        assert "improved" in result


# ────────────────────────────────────────────
# _debug_verify_loras log level
# ────────────────────────────────────────────


class TestDebugVerifyLoras:
    """Test _debug_verify_loras uses correct log levels."""

    def _verify_loras(self, ctx, caplog):
        from services.generation_prompt import _debug_verify_loras

        with caplog.at_level(logging.DEBUG):
            _debug_verify_loras(ctx)

    def test_lora_found_logs_debug(self, caplog):
        ctx = GenerationContext(request=_make_request())
        ctx.prompt = "1girl, <lora:test:0.8>"
        ctx.character = _make_character()
        self._verify_loras(ctx, caplog)
        assert any("LoRA Check" in r.message and r.levelno == logging.DEBUG for r in caplog.records)

    def test_no_lora_with_character_logs_warning(self, caplog):
        ctx = GenerationContext(request=_make_request())
        ctx.prompt = "1girl, standing"
        ctx.character = _make_character()
        self._verify_loras(ctx, caplog)
        assert any("LoRA Check" in r.message and r.levelno == logging.WARNING for r in caplog.records)

    def test_no_lora_background_scene_logs_debug(self, caplog):
        """Background/narrator scene (no character) should NOT emit WARNING."""
        ctx = GenerationContext(request=_make_request(character_id=None))
        ctx.prompt = "no_humans, bedroom, night"
        ctx.character = None
        self._verify_loras(ctx, caplog)
        lora_records = [r for r in caplog.records if "LoRA Check" in r.message]
        assert len(lora_records) == 1
        assert lora_records[0].levelno == logging.DEBUG
        assert "background/narrator" in lora_records[0].message
