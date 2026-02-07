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

    def _mock_db(self, profile_loras=None, default_positive="masterpiece", default_negative="lowres"):
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
