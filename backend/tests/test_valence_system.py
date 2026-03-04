"""Tests for Expression-Mood Valence conflict detection system.

Covers: TagValenceCache, _flatten_layers valence check,
        _prompt_conflict_resolver valence conflicts, LLM valence classifier.
"""

from unittest.mock import MagicMock, patch

import pytest

from services.keywords.db_cache import TagValenceCache

# ────────────────────────────────────────────
# TagValenceCache Unit Tests
# ────────────────────────────────────────────


class TestTagValenceCache:
    """TagValenceCache 단위 테스트."""

    def setup_method(self):
        """Reset cache before each test."""
        TagValenceCache._initialized = False
        TagValenceCache._cache.clear()

    def test_get_valence_returns_cached_value(self):
        TagValenceCache._cache = {"smile": "positive", "crying": "negative"}
        TagValenceCache._initialized = True
        assert TagValenceCache.get_valence("smile") == "positive"
        assert TagValenceCache.get_valence("crying") == "negative"

    def test_get_valence_returns_none_for_unknown(self):
        TagValenceCache._cache = {"smile": "positive"}
        TagValenceCache._initialized = True
        assert TagValenceCache.get_valence("unknown_tag") is None

    def test_get_valence_normalizes_input(self):
        TagValenceCache._cache = {"looking_at_viewer": "neutral"}
        TagValenceCache._initialized = True
        assert TagValenceCache.get_valence("looking at viewer") == "neutral"
        assert TagValenceCache.get_valence("LOOKING_AT_VIEWER") == "neutral"

    def test_is_valence_conflicting_positive_vs_negative(self):
        TagValenceCache._cache = {"smile": "positive", "melancholic": "negative"}
        TagValenceCache._initialized = True
        assert TagValenceCache.is_valence_conflicting("smile", "melancholic") is True

    def test_is_valence_conflicting_same_polarity(self):
        TagValenceCache._cache = {"smile": "positive", "romantic": "positive"}
        TagValenceCache._initialized = True
        assert TagValenceCache.is_valence_conflicting("smile", "romantic") is False

    def test_is_valence_conflicting_neutral_allows_any(self):
        TagValenceCache._cache = {"serious": "neutral", "melancholic": "negative"}
        TagValenceCache._initialized = True
        assert TagValenceCache.is_valence_conflicting("serious", "melancholic") is False

    def test_is_valence_conflicting_none_valence_allows(self):
        TagValenceCache._cache = {"smile": "positive"}
        TagValenceCache._initialized = True
        # "unknown_tag" has no valence (None) → not conflicting
        assert TagValenceCache.is_valence_conflicting("smile", "unknown_tag") is False

    def test_is_valence_conflicting_both_none(self):
        TagValenceCache._cache = {}
        TagValenceCache._initialized = True
        assert TagValenceCache.is_valence_conflicting("tag_a", "tag_b") is False

    def test_is_valence_conflicting_negative_vs_positive(self):
        TagValenceCache._cache = {"angry": "negative", "cozy": "positive"}
        TagValenceCache._initialized = True
        assert TagValenceCache.is_valence_conflicting("angry", "cozy") is True

    def test_refresh_clears_and_reinitializes(self):
        TagValenceCache._cache = {"old": "positive"}
        TagValenceCache._initialized = True

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        TagValenceCache.refresh(mock_db)

        assert "old" not in TagValenceCache._cache
        assert TagValenceCache._initialized is True


# ────────────────────────────────────────────
# _flatten_layers Valence Integration Tests
# ────────────────────────────────────────────


class _FakeValenceCache:
    _initialized = True
    _data = {
        "smile": "positive",
        "happy": "positive",
        "romantic": "positive",
        "crying": "negative",
        "melancholic": "negative",
        "angry": "negative",
        "serious": "neutral",
    }

    @classmethod
    def initialize(cls, db):
        pass

    @classmethod
    def get_valence(cls, tag):
        return cls._data.get(tag.lower().replace(" ", "_").strip())

    @classmethod
    def is_valence_conflicting(cls, tag1, tag2):
        v1 = cls.get_valence(tag1)
        v2 = cls.get_valence(tag2)
        if not v1 or not v2 or v1 == "neutral" or v2 == "neutral":
            return False
        return v1 != v2


class _FakeRuleCache:
    _initialized = True

    @classmethod
    def initialize(cls, db):
        pass

    @classmethod
    def is_conflicting(cls, tag1, tag2):
        return False


class TestFlattenLayersValence:
    """_flatten_layers에서 valence 교차 충돌 감지 테스트."""

    def _make_builder(self):
        from services.prompt.composition import PromptBuilder

        mock_db = MagicMock()
        builder = PromptBuilder.__new__(PromptBuilder)
        builder.db = mock_db
        builder._last_composed_layers = None
        return builder

    @patch("services.prompt.composition.TagRuleCache", _FakeRuleCache)
    @patch("services.keywords.db_cache.TagValenceCache", _FakeValenceCache)
    def test_smile_melancholic_drops_melancholic(self):
        """smile(L7, positive) + melancholic(L11, negative) → melancholic 제거."""
        from services.prompt.composition import LAYER_ATMOSPHERE, LAYER_EXPRESSION

        builder = self._make_builder()
        layers = [[] for _ in range(12)]
        layers[LAYER_EXPRESSION] = ["smile"]
        layers[LAYER_ATMOSPHERE] = ["melancholic"]

        result = builder._flatten_layers(layers)
        assert "smile" in result
        assert "melancholic" not in result

    @patch("services.prompt.composition.TagRuleCache", _FakeRuleCache)
    @patch("services.keywords.db_cache.TagValenceCache", _FakeValenceCache)
    def test_smile_romantic_both_kept(self):
        """smile(positive) + romantic(positive) → 둘 다 유지."""
        from services.prompt.composition import LAYER_ATMOSPHERE, LAYER_EXPRESSION

        builder = self._make_builder()
        layers = [[] for _ in range(12)]
        layers[LAYER_EXPRESSION] = ["smile"]
        layers[LAYER_ATMOSPHERE] = ["romantic"]

        result = builder._flatten_layers(layers)
        assert "smile" in result
        assert "romantic" in result

    @patch("services.prompt.composition.TagRuleCache", _FakeRuleCache)
    @patch("services.keywords.db_cache.TagValenceCache", _FakeValenceCache)
    def test_neutral_expression_allows_any_mood(self):
        """serious(neutral) + melancholic(negative) → 둘 다 유지."""
        from services.prompt.composition import LAYER_ATMOSPHERE, LAYER_EXPRESSION

        builder = self._make_builder()
        layers = [[] for _ in range(12)]
        layers[LAYER_EXPRESSION] = ["serious"]
        layers[LAYER_ATMOSPHERE] = ["melancholic"]

        result = builder._flatten_layers(layers)
        assert "serious" in result
        assert "melancholic" in result

    @patch("services.prompt.composition.TagRuleCache", _FakeRuleCache)
    @patch("services.keywords.db_cache.TagValenceCache", _FakeValenceCache)
    def test_angry_romantic_drops_romantic(self):
        """angry(negative, L7) + romantic(positive, L11) → romantic 제거."""
        from services.prompt.composition import LAYER_ATMOSPHERE, LAYER_EXPRESSION

        builder = self._make_builder()
        layers = [[] for _ in range(12)]
        layers[LAYER_EXPRESSION] = ["angry"]
        layers[LAYER_ATMOSPHERE] = ["romantic"]

        result = builder._flatten_layers(layers)
        assert "angry" in result
        assert "romantic" not in result

    @patch("services.prompt.composition.TagRuleCache", _FakeRuleCache)
    @patch("services.keywords.db_cache.TagValenceCache", _FakeValenceCache)
    def test_non_valence_layers_unaffected(self):
        """non-valence 레이어 (L9, L10 등)는 valence 체크 안 함."""
        from services.prompt.composition import LAYER_CAMERA, LAYER_ENVIRONMENT

        builder = self._make_builder()
        layers = [[] for _ in range(12)]
        layers[LAYER_CAMERA] = ["close-up"]
        layers[LAYER_ENVIRONMENT] = ["outdoors"]

        result = builder._flatten_layers(layers)
        assert "close-up" in result
        assert "outdoors" in result

    @patch("services.prompt.composition.TagRuleCache", _FakeRuleCache)
    @patch("services.keywords.db_cache.TagValenceCache", _FakeValenceCache)
    def test_unknown_valence_tag_passes(self):
        """valence 미분류 태그는 충돌 체크 없이 통과."""
        from services.prompt.composition import LAYER_ATMOSPHERE, LAYER_EXPRESSION

        builder = self._make_builder()
        layers = [[] for _ in range(12)]
        layers[LAYER_EXPRESSION] = ["unknown_expression"]
        layers[LAYER_ATMOSPHERE] = ["melancholic"]

        result = builder._flatten_layers(layers)
        assert "unknown_expression" in result
        assert "melancholic" in result


# ────────────────────────────────────────────
# _prompt_conflict_resolver Valence Tests
# ────────────────────────────────────────────


class _FakeCategoryCache:
    _initialized = True

    @classmethod
    def initialize(cls, db):
        pass

    @classmethod
    def get_category(cls, token):
        mapping = {
            "smile": "expression",
            "melancholic": "mood",
            "romantic": "mood",
            "serious": "expression",
            "1girl": "subject",
            "blue_hair": "hair_color",
        }
        return mapping.get(token.lower().replace(" ", "_").strip())


class TestResolveValenceConflicts:
    """_resolve_valence_conflicts 테스트."""

    def _scenes(self, prompts):
        return [{"image_prompt": p} for p in prompts]

    @patch("services.keywords.db_cache.TagValenceCache", _FakeValenceCache)
    @patch("services.keywords.db_cache.TagCategoryCache", _FakeCategoryCache)
    def test_smile_melancholic_removes_melancholic(self):
        from services.agent.nodes._prompt_conflict_resolver import _resolve_valence_conflicts

        scenes = self._scenes(["1girl, smile, melancholic, blue_hair"])
        _resolve_valence_conflicts(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert "smile" in tokens
        assert "melancholic" not in tokens
        assert "1girl" in tokens
        assert "blue_hair" in tokens

    @patch("services.keywords.db_cache.TagValenceCache", _FakeValenceCache)
    @patch("services.keywords.db_cache.TagCategoryCache", _FakeCategoryCache)
    def test_smile_romantic_both_kept(self):
        from services.agent.nodes._prompt_conflict_resolver import _resolve_valence_conflicts

        scenes = self._scenes(["1girl, smile, romantic"])
        _resolve_valence_conflicts(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert "smile" in tokens
        assert "romantic" in tokens

    @patch("services.keywords.db_cache.TagValenceCache", _FakeValenceCache)
    @patch("services.keywords.db_cache.TagCategoryCache", _FakeCategoryCache)
    def test_neutral_expression_allows_any(self):
        from services.agent.nodes._prompt_conflict_resolver import _resolve_valence_conflicts

        scenes = self._scenes(["1girl, serious, melancholic"])
        _resolve_valence_conflicts(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert "serious" in tokens
        assert "melancholic" in tokens

    @patch("services.keywords.db_cache.TagValenceCache", _FakeValenceCache)
    @patch("services.keywords.db_cache.TagCategoryCache", _FakeCategoryCache)
    def test_empty_prompt_skipped(self):
        from services.agent.nodes._prompt_conflict_resolver import _resolve_valence_conflicts

        scenes = [{"image_prompt": ""}]
        _resolve_valence_conflicts(scenes)
        assert scenes[0]["image_prompt"] == ""


# ────────────────────────────────────────────
# LLM Valence Classifier Tests
# ────────────────────────────────────────────


class TestValencePromptAndValidation:
    """LLM valence 프롬프트 빌드 + 응답 검증 테스트."""

    def test_build_valence_prompt_includes_tags(self):
        from services.tag_classifier_llm import _build_valence_prompt

        prompt = _build_valence_prompt(["smile", "crying", "serious"])
        assert "smile" in prompt
        assert "crying" in prompt
        assert "serious" in prompt
        assert "positive" in prompt
        assert "negative" in prompt
        assert "neutral" in prompt

    def test_validate_valence_results_valid(self):
        from services.tag_classifier_llm import _validate_valence_results

        raw = [
            {"tag": "smile", "valence": "positive", "confidence": 0.95},
            {"tag": "crying", "valence": "negative", "confidence": 0.9},
            {"tag": "serious", "valence": "neutral", "confidence": 0.8},
        ]
        results = _validate_valence_results(raw)
        assert len(results) == 3
        assert results[0]["valence"] == "positive"
        assert results[1]["valence"] == "negative"

    def test_validate_valence_results_filters_invalid(self):
        from services.tag_classifier_llm import _validate_valence_results

        raw = [
            {"tag": "smile", "valence": "positive", "confidence": 0.9},
            {"tag": "test", "valence": "unknown_value", "confidence": 0.5},  # invalid valence
            {"tag": "", "valence": "positive", "confidence": 0.5},  # empty tag
            {"valence": "positive", "confidence": 0.5},  # missing tag
        ]
        results = _validate_valence_results(raw)
        assert len(results) == 1
        assert results[0]["tag"] == "smile"

    def test_validate_valence_results_clamps_confidence(self):
        from services.tag_classifier_llm import _validate_valence_results

        raw = [
            {"tag": "smile", "valence": "positive", "confidence": 1.5},
            {"tag": "cry", "valence": "negative", "confidence": -0.3},
        ]
        results = _validate_valence_results(raw)
        assert results[0]["confidence"] == 1.0
        assert results[1]["confidence"] == 0.0


# ────────────────────────────────────────────
# Tag Model Valence Validation Tests
# ────────────────────────────────────────────


class TestTagValenceValidation:
    """Tag.valence 모델 검증 테스트."""

    def test_valid_valence_values(self):
        from models.tag import Tag

        tag = Tag(name="smile", valence="positive")
        assert tag.valence == "positive"

        tag2 = Tag(name="crying", valence="negative")
        assert tag2.valence == "negative"

        tag3 = Tag(name="serious", valence="neutral")
        assert tag3.valence == "neutral"

    def test_none_valence_allowed(self):
        from models.tag import Tag

        tag = Tag(name="test_tag", valence=None)
        assert tag.valence is None

    def test_invalid_valence_raises(self):
        from models.tag import Tag

        with pytest.raises(ValueError, match="Invalid valence"):
            Tag(name="test_tag", valence="invalid")
