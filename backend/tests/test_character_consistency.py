"""Tests for CharacterConsistencyResolver."""

from unittest.mock import MagicMock, patch

from services.character_consistency import (
    CharacterConsistencyResolver,
    ConsistencyRequest,
    ConsistencyStrategy,
)


def _make_character(
    name="test_char",
    loras=None,
    ip_adapter_weight=None,
    ip_adapter_model=None,
):
    char = MagicMock()
    char.name = name
    char.loras = loras
    char.ip_adapter_weight = ip_adapter_weight
    char.ip_adapter_model = ip_adapter_model
    return char


def _make_lora(name="test_lora", lora_type="character", trigger_words=None, default_weight=0.7):
    lora = MagicMock()
    lora.name = name
    lora.lora_type = lora_type
    lora.trigger_words = trigger_words or []
    lora.default_weight = default_weight
    return lora


class TestConsistencyStrategyDefaults:
    def test_default_strategy_for_none_character(self):
        db = MagicMock()
        resolver = CharacterConsistencyResolver(db)
        strategy = resolver.resolve(None)

        assert strategy.quality_score == "low"
        assert strategy.ip_adapter_enabled is False
        assert strategy.reference_only_enabled is False
        assert strategy.style_loras == ()
        assert strategy.style_lora_source == "none"

    def test_frozen_dataclass(self):
        strategy = ConsistencyStrategy()
        try:
            strategy.quality_score = "high"  # type: ignore[misc]
            raise AssertionError("Should raise FrozenInstanceError")
        except AttributeError:
            pass


class TestStyleLoRAResolution:
    def test_style_profile_takes_priority(self):
        db = MagicMock()
        resolver = CharacterConsistencyResolver(db)
        style_profile = [{"name": "anime_style", "weight": 0.8, "trigger_words": []}]

        strategy = resolver.resolve(
            _make_character(loras=[{"lora_id": 1, "weight": 0.5}]),
            style_profile_loras=style_profile,
        )

        assert strategy.style_lora_source == "style_profile"
        assert len(strategy.style_loras) == 1
        assert strategy.style_loras[0]["name"] == "anime_style"

    @patch("services.character_consistency.load_reference_image", return_value=None)
    def test_character_style_lora_fallback(self, mock_ref):
        db = MagicMock()
        style_lora = _make_lora(name="flat_color", lora_type="style", default_weight=0.8)
        db.query.return_value.filter.return_value.first.return_value = style_lora

        resolver = CharacterConsistencyResolver(db)
        character = _make_character(loras=[{"lora_id": 1, "weight": 0.8}])

        strategy = resolver.resolve(character, style_profile_loras=None)

        assert strategy.style_lora_source == "character_fallback"
        assert len(strategy.style_loras) == 1
        assert strategy.style_loras[0]["name"] == "flat_color"
        # Fallback weight capped at 0.5
        assert strategy.style_loras[0]["weight"] <= 0.5

    @patch("services.character_consistency.load_reference_image", return_value=None)
    def test_no_style_lora_source(self, mock_ref):
        db = MagicMock()
        char_lora = _make_lora(name="char_lora", lora_type="character")
        db.query.return_value.filter.return_value.first.return_value = char_lora

        resolver = CharacterConsistencyResolver(db)
        character = _make_character(loras=[{"lora_id": 1, "weight": 0.7}])

        strategy = resolver.resolve(character, style_profile_loras=None)

        assert strategy.style_lora_source == "none"
        assert len(strategy.style_loras) == 0


class TestIPAdapterResolution:
    @patch("config.IP_ADAPTER_AUTO_ENABLE", True)
    @patch("services.character_consistency.load_reference_image", return_value="base64_image_data")
    def test_auto_enable_with_reference_image(self, mock_ref):
        db = MagicMock()
        resolver = CharacterConsistencyResolver(db)
        character = _make_character(name="Midoriya", ip_adapter_weight=0.4)

        strategy = resolver.resolve(character)

        assert strategy.ip_adapter_enabled is True
        assert strategy.ip_adapter_reference == "Midoriya"
        assert strategy.ip_adapter_weight == 0.4

    @patch("services.character_consistency.load_reference_image", return_value=None)
    def test_no_reference_image_warns(self, mock_ref):
        db = MagicMock()
        resolver = CharacterConsistencyResolver(db)
        character = _make_character(name="NoRef")

        strategy = resolver.resolve(character, req=ConsistencyRequest(use_ip_adapter=True))

        assert strategy.ip_adapter_enabled is False
        assert any("참조 이미지가 없어" in w for w in strategy.warnings)

    @patch("services.character_consistency.load_reference_image", return_value="base64_image_data")
    def test_explicit_ip_adapter_reference(self, mock_ref):
        db = MagicMock()
        resolver = CharacterConsistencyResolver(db)
        character = _make_character(name="TestChar")

        strategy = resolver.resolve(
            character,
            req=ConsistencyRequest(
                use_ip_adapter=True,
                ip_adapter_reference="OtherChar",
                ip_adapter_weight=0.5,
            ),
        )

        # Explicit reference is used directly without auto-enable
        assert strategy.ip_adapter_enabled is True
        assert strategy.ip_adapter_reference == "OtherChar"
        assert strategy.ip_adapter_weight == 0.5


class TestReferenceOnlyMutualExclusion:
    @patch("config.IP_ADAPTER_AUTO_ENABLE", True)
    @patch("services.character_consistency.load_reference_image", return_value="base64_image_data")
    def test_ip_adapter_disables_reference_only(self, mock_ref):
        db = MagicMock()
        resolver = CharacterConsistencyResolver(db)
        character = _make_character()

        strategy = resolver.resolve(
            character,
            req=ConsistencyRequest(use_reference_only=True),
        )

        # IP-Adapter auto-enabled (reference image exists) → reference_only skipped
        assert strategy.ip_adapter_enabled is True
        assert strategy.reference_only_enabled is False

    @patch("services.character_consistency.load_reference_image", return_value=None)
    def test_reference_only_when_no_ip_adapter(self, mock_ref):
        db = MagicMock()
        resolver = CharacterConsistencyResolver(db)
        character = _make_character()

        strategy = resolver.resolve(
            character,
            req=ConsistencyRequest(use_reference_only=True),
        )

        # No reference image → IP-Adapter disabled → reference_only kept
        assert strategy.ip_adapter_enabled is False
        assert strategy.reference_only_enabled is True


class TestQualityAssessment:
    @patch("config.IP_ADAPTER_AUTO_ENABLE", True)
    @patch("services.character_consistency.load_reference_image", return_value="base64_image_data")
    def test_high_quality_with_lora_and_ip_adapter(self, mock_ref):
        db = MagicMock()
        char_lora = _make_lora(name="char_lora", lora_type="character")
        db.query.return_value.filter.return_value.first.return_value = char_lora

        resolver = CharacterConsistencyResolver(db)
        character = _make_character(loras=[{"lora_id": 1, "weight": 0.7}])

        strategy = resolver.resolve(character)

        assert strategy.quality_score == "high"

    @patch("services.character_consistency.load_reference_image", return_value=None)
    def test_medium_quality_with_lora_only(self, mock_ref):
        db = MagicMock()
        char_lora = _make_lora(name="char_lora", lora_type="character")
        db.query.return_value.filter.return_value.first.return_value = char_lora

        resolver = CharacterConsistencyResolver(db)
        character = _make_character(loras=[{"lora_id": 1, "weight": 0.7}])

        strategy = resolver.resolve(character)

        assert strategy.quality_score == "medium"

    @patch("services.character_consistency.load_reference_image", return_value=None)
    def test_low_quality_tags_only_warns(self, mock_ref):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        resolver = CharacterConsistencyResolver(db)
        character = _make_character(loras=None)

        strategy = resolver.resolve(character)

        assert strategy.quality_score == "low"
        assert any("일관성이 낮을 수 있습니다" in w for w in strategy.warnings)
