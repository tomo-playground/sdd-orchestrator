"""Tests for prompt_pre_composed flag routing and skip_loras parameter."""

from unittest.mock import MagicMock, patch

from schemas import SceneGenerateRequest
from services.generation import _prepare_prompt, _resolve_style_loras, apply_style_profile_to_prompt


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


# ────────────────────────────────────────────
# prompt_pre_composed flag routing
# ────────────────────────────────────────────


class TestPreparePromptFlag:
    """Test prompt_pre_composed flag behavior in _prepare_prompt."""

    @patch("services.generation.load_reference_image", return_value=None)
    @patch("services.generation.apply_style_profile_to_prompt")
    def test_pre_composed_skips_v3(self, mock_style, mock_ref):
        """prompt_pre_composed=True → V3 not called, prompt used as-is."""
        mock_style.return_value = ("quality, 1girl, standing, <lora:style:0.7>", "bad")
        req = _make_request(prompt_pre_composed=True, prompt="masterpiece, 1girl, standing")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation.V3PromptService") as mock_v3:
            cleaned, warnings, char = _prepare_prompt(req, db)

        mock_v3.assert_not_called()
        mock_style.assert_called_once()
        # skip_loras should NOT be passed (defaults to False for pre-composed)
        call_kwargs = mock_style.call_args
        assert call_kwargs.kwargs.get("skip_loras", False) is False

    @patch("services.generation.load_reference_image", return_value=None)
    @patch("services.generation._resolve_style_loras", return_value=[])
    @patch("services.generation.apply_style_profile_to_prompt")
    def test_raw_prompt_runs_v3(self, mock_style, mock_resolve, mock_ref):
        """prompt_pre_composed=False + character → V3 injects character LoRA."""
        mock_style.return_value = ("quality, 1girl, standing", "bad")
        req = _make_request(prompt_pre_composed=False)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation.V3PromptService") as mock_v3:
            mock_v3.return_value.generate_prompt_for_scene.return_value = "v3_composed"
            cleaned, warnings, char = _prepare_prompt(req, db)

        mock_v3.assert_called_once_with(db)
        mock_v3.return_value.generate_prompt_for_scene.assert_called_once()
        assert cleaned == "v3_composed"
        # skip_loras=True for raw prompt path
        call_kwargs = mock_style.call_args
        assert call_kwargs.kwargs.get("skip_loras") is True

    @patch("services.generation.load_reference_image", return_value=None)
    @patch("services.generation.apply_style_profile_to_prompt")
    def test_no_character_applies_full_style_profile(self, mock_style, mock_ref):
        """No character_id → full style profile applied, V3 not called."""
        mock_style.return_value = ("quality, scenery, sunset", "bad")
        req = _make_request(character_id=None)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("services.generation.V3PromptService") as mock_v3:
            cleaned, warnings, char = _prepare_prompt(req, db)

        mock_v3.assert_not_called()
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
        group.config = MagicMock()
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

    @patch("services.generation.load_reference_image", return_value=None)
    @patch("services.generation._resolve_style_loras")
    @patch("services.generation.apply_style_profile_to_prompt")
    def test_batch_ignores_frontend_style_loras(self, mock_style, mock_resolve, mock_ref):
        """Even when frontend sends style_loras, DB resolution is used (SSOT)."""
        mock_style.return_value = ("quality, 1girl, standing", "bad")
        mock_resolve.return_value = [{"name": "flat_color", "weight": 0.7, "trigger_words": ["flat color"]}]
        # Frontend sends {lora_id, weight} format (no name/trigger_words)
        req = _make_request(
            prompt_pre_composed=False,
            style_loras=[{"lora_id": 5, "weight": 0.7}],
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation.V3PromptService") as mock_v3:
            mock_v3.return_value.generate_prompt_for_scene.return_value = "composed"
            _prepare_prompt(req, db)

        # V3 must receive DB-resolved loras (with name), NOT frontend format
        call_args = mock_v3.return_value.generate_prompt_for_scene.call_args
        style_loras_used = call_args.kwargs.get("style_loras", call_args[1].get("style_loras"))
        assert style_loras_used[0]["name"] == "flat_color"
        assert "trigger_words" in style_loras_used[0]

    @patch("services.generation.load_reference_image", return_value=None)
    @patch("services.generation._resolve_style_loras")
    @patch("services.generation.apply_style_profile_to_prompt")
    def test_batch_uses_db_even_with_empty_frontend_loras(self, mock_style, mock_resolve, mock_ref):
        """DB resolution is always used regardless of frontend style_loras."""
        mock_style.return_value = ("quality, 1girl", "bad")
        mock_resolve.return_value = [{"name": "flat_color", "weight": 0.7, "trigger_words": ["flat color"]}]
        req = _make_request(prompt_pre_composed=False, style_loras=[])
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = _make_character()

        with patch("services.generation.V3PromptService") as mock_v3:
            mock_v3.return_value.generate_prompt_for_scene.return_value = "composed"
            _prepare_prompt(req, db)

        # Even with empty frontend loras, DB is consulted
        mock_resolve.assert_called_once()
        call_args = mock_v3.return_value.generate_prompt_for_scene.call_args
        style_loras_used = call_args.kwargs.get("style_loras", call_args[1].get("style_loras"))
        assert len(style_loras_used) == 1
        assert style_loras_used[0]["name"] == "flat_color"


# ────────────────────────────────────────────
# Narrator background scene filtering
# ────────────────────────────────────────────


class TestNarratorBackgroundFiltering:
    """Test Narrator (no_humans) scenes route through V3 background composition."""

    @patch("services.generation.load_reference_image", return_value=None)
    @patch("services.generation._resolve_style_loras", return_value=[])
    @patch("services.generation.apply_style_profile_to_prompt")
    def test_narrator_no_humans_runs_v3_compose(self, mock_style, mock_resolve, mock_ref):
        """no_humans + character_id=None → V3 compose() is called."""
        mock_style.return_value = ("no_humans, bedroom, night, full_body, standing", "bad")
        req = _make_request(character_id=None, prompt="no_humans, bedroom, night, full_body, standing")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("services.prompt.v3_composition.V3PromptBuilder") as mock_builder_cls:
            mock_builder = mock_builder_cls.return_value
            mock_builder.compose.return_value = "no_humans, bedroom, night"
            cleaned, warnings, char = _prepare_prompt(req, db)

        mock_builder_cls.assert_called_once_with(db)
        mock_builder.compose.assert_called_once()
        assert cleaned == "no_humans, bedroom, night"
        # skip_loras=True for narrator path
        call_kwargs = mock_style.call_args
        assert call_kwargs.kwargs.get("skip_loras") is True

    @patch("services.generation.load_reference_image", return_value=None)
    @patch("services.generation._resolve_style_loras", return_value=[])
    @patch("services.generation.apply_style_profile_to_prompt")
    def test_narrator_filters_character_tags(self, mock_style, mock_resolve, mock_ref):
        """V3 compose() strips full_body, standing from no_humans scenes."""
        mock_style.return_value = ("no_humans, bedroom, full_body, standing", "bad")
        req = _make_request(character_id=None, prompt="no_humans, bedroom, full_body, standing")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("services.prompt.v3_composition.V3PromptBuilder") as mock_builder_cls:
            # Simulate V3 compose stripping character tags
            mock_builder_cls.return_value.compose.return_value = "no_humans, bedroom"
            cleaned, _, _ = _prepare_prompt(req, db)

        assert "full_body" not in cleaned
        assert "standing" not in cleaned

    @patch("services.generation.load_reference_image", return_value=None)
    @patch("services.generation._resolve_style_loras", return_value=[])
    @patch("services.generation.apply_style_profile_to_prompt")
    def test_narrator_preserves_environment_tags(self, mock_style, mock_resolve, mock_ref):
        """Environment tags (bedroom, night) are preserved through V3 compose."""
        mock_style.return_value = ("no_humans, bedroom, night", "bad")
        req = _make_request(character_id=None, prompt="no_humans, bedroom, night")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("services.prompt.v3_composition.V3PromptBuilder") as mock_builder_cls:
            mock_builder_cls.return_value.compose.return_value = "no_humans, bedroom, night"
            cleaned, _, _ = _prepare_prompt(req, db)

        assert "bedroom" in cleaned
        assert "night" in cleaned
        assert "no_humans" in cleaned

    @patch("services.generation.load_reference_image", return_value=None)
    @patch("services.generation._resolve_style_loras")
    @patch("services.generation.apply_style_profile_to_prompt")
    def test_narrator_applies_style_loras(self, mock_style, mock_resolve, mock_ref):
        """style_loras are passed to V3 compose() for Narrator scenes."""
        style_loras = [{"name": "flat_color", "weight": 0.7, "trigger_words": ["flat color"]}]
        mock_resolve.return_value = style_loras
        mock_style.return_value = ("no_humans, bedroom", "bad")
        req = _make_request(character_id=None, prompt="no_humans, bedroom")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("services.prompt.v3_composition.V3PromptBuilder") as mock_builder_cls:
            mock_builder_cls.return_value.compose.return_value = "no_humans, bedroom, <lora:flat_color:0.7>"
            cleaned, _, _ = _prepare_prompt(req, db)

        call_kwargs = mock_builder_cls.return_value.compose.call_args
        assert call_kwargs.kwargs.get("style_loras") == style_loras

    @patch("services.generation.load_reference_image", return_value=None)
    @patch("services.generation.apply_style_profile_to_prompt")
    def test_non_narrator_no_character_unchanged(self, mock_style, mock_ref):
        """No no_humans + no character_id → existing path (full style, no V3)."""
        mock_style.return_value = ("scenery, sunset, mountain", "bad")
        req = _make_request(character_id=None, prompt="scenery, sunset, mountain")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("services.prompt.v3_composition.V3PromptBuilder") as mock_builder_cls:
            cleaned, _, char = _prepare_prompt(req, db)

        mock_builder_cls.assert_not_called()
        assert char is None
        # skip_loras should NOT be passed (full style profile)
        call_kwargs = mock_style.call_args
        assert call_kwargs.kwargs.get("skip_loras", False) is False
