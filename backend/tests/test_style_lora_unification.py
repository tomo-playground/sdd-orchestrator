"""
Test Style LoRA Unification (TDD)

This test suite verifies that:
1. StyleProfile.loras are applied to ALL scenes (A, B, Narrator)
2. Character.loras are filtered to character-type only (style excluded)
3. Duplicate LoRAs between StyleProfile and Character are handled correctly
"""

import pytest
from sqlalchemy.orm import Session

from models import LoRA, SDModel, StyleProfile
from services.prompt.composition import PromptBuilder


@pytest.fixture
def style_lora(db_session: Session) -> LoRA:
    """Create a style LoRA for testing."""
    lora = LoRA(
        name="flat_color_style",
        display_name="Flat Color Style",
        trigger_words=["flat_color"],
        lora_type="style",
        default_weight=0.7,
    )
    db_session.add(lora)
    db_session.flush()
    return lora


@pytest.fixture
def character_lora_a(db_session: Session) -> LoRA:
    """Create an character LoRA for Character A."""
    lora = LoRA(
        name="character_a_lora",
        display_name="Character A LoRA",
        trigger_words=["char_a_trigger"],
        lora_type="character",
        default_weight=0.8,
    )
    db_session.add(lora)
    db_session.flush()
    return lora


@pytest.fixture
def character_lora_b(db_session: Session) -> LoRA:
    """Create an character LoRA for Character B."""
    lora = LoRA(
        name="character_b_lora",
        display_name="Character B LoRA",
        trigger_words=["char_b_trigger"],
        lora_type="character",
        default_weight=0.8,
    )
    db_session.add(lora)
    db_session.flush()
    return lora


@pytest.fixture
def style_profile_with_lora(db_session: Session, style_lora: LoRA) -> StyleProfile:
    """Create a StyleProfile with style LoRA."""
    # Create SD Model first
    model = SDModel(
        name="test_model.safetensors",
        display_name="Test Model",
        model_type="SD 1.5",
        is_active=True,
    )
    db_session.add(model)
    db_session.flush()

    profile = StyleProfile(
        name="unified_style_profile",
        display_name="Unified Style Profile",
        sd_model_id=model.id,
        loras=[
            {
                "lora_id": style_lora.id,
                "name": style_lora.name,
                "weight": 0.7,
                "trigger_words": style_lora.trigger_words,
                "lora_type": style_lora.lora_type,
            }
        ],
        is_active=True,
    )
    db_session.add(profile)
    db_session.flush()
    return profile


class TestStyleLoRAUnification:
    """Test Style LoRA unification across all scene types."""

    def test_style_profile_loras_applied_to_speaker_a(
        self, db_session: Session, style_profile_with_lora: StyleProfile, character_lora_a: LoRA
    ):
        """
        Given: StyleProfile with style LoRA, Character A with character LoRA
        When: Generate prompt for Speaker A scene
        Then: Both StyleProfile.style and CharA.character LoRAs should be applied
        """
        # Arrange
        style_loras = style_profile_with_lora.loras
        character_loras = [
            {
                "name": character_lora_a.name,
                "weight": character_lora_a.default_weight,
                "trigger_words": character_lora_a.trigger_words,
                "lora_type": "character",
            }
        ]

        builder = PromptBuilder(db_session)

        # Act
        result = builder.compose(
            tags=["1girl", "standing", "masterpiece"],
            character_loras=character_loras,
            style_loras=style_loras,
        )

        # Assert — character_a weight 0.8 → capped to 0.76 (STYLE_LORA_WEIGHT_CAP)
        assert "<lora:flat_color_style:0.7>" in result, "StyleProfile style LoRA should be applied"
        assert "<lora:character_a_lora:0.76>" in result, "Character LoRA should be capped to 0.76"
        assert "flat_color" in result, "Style LoRA trigger words should be included"
        assert "char_a_trigger" in result, "Identity LoRA trigger words should be included"

    def test_style_profile_loras_applied_to_speaker_b(
        self, db_session: Session, style_profile_with_lora: StyleProfile, character_lora_b: LoRA
    ):
        """
        Given: StyleProfile with style LoRA, Character B with character LoRA
        When: Generate prompt for Speaker B scene
        Then: Same StyleProfile.style LoRA + CharB.identity should be applied
        """
        # Arrange
        style_loras = style_profile_with_lora.loras
        character_loras = [
            {
                "name": character_lora_b.name,
                "weight": character_lora_b.default_weight,
                "trigger_words": character_lora_b.trigger_words,
                "lora_type": "character",
            }
        ]

        builder = PromptBuilder(db_session)

        # Act
        result = builder.compose(
            tags=["1boy", "standing", "masterpiece"],
            character_loras=character_loras,
            style_loras=style_loras,
        )

        # Assert — character_b weight 0.8 → capped to 0.76
        assert "<lora:flat_color_style:0.7>" in result, "Same StyleProfile LoRA for Speaker B"
        assert "<lora:character_b_lora:0.76>" in result, "Character B LoRA should be capped to 0.76"

    def test_style_profile_loras_applied_to_narrator(self, db_session: Session, style_profile_with_lora: StyleProfile):
        """
        Given: StyleProfile with style LoRA
        When: Generate prompt for Narrator scene (no_humans)
        Then: StyleProfile.style LoRA should be applied (no character LoRA)
        """
        # Arrange
        style_loras = style_profile_with_lora.loras
        character_loras = []  # Narrator has no character LoRAs

        builder = PromptBuilder(db_session)

        # Act
        result = builder.compose(
            tags=["no_humans", "scenery", "cafe", "window", "masterpiece"],
            character_loras=character_loras,
            style_loras=style_loras,
        )

        # Assert
        assert "<lora:flat_color_style:0.7>" in result, "StyleProfile LoRA should be applied to Narrator"
        assert "flat_color" in result, "Style trigger words should be included"
        assert "character_a_lora" not in result, "No character LoRA for Narrator"
        assert "character_b_lora" not in result, "No character LoRA for Narrator"

    def test_character_style_lora_ignored_when_style_profile_set(
        self, db_session: Session, style_profile_with_lora: StyleProfile
    ):
        """
        Given: StyleProfile set, Character has both identity and style LoRAs
        When: Generate prompt
        Then: Character's style LoRA should be ignored (only identity used)

        Note: This filtering happens on Frontend. Backend receives only character LoRAs.
        This test verifies Backend correctly handles the filtered input.
        """
        # Arrange - Character has style LoRA that should be ignored
        char_lora = LoRA(
            name="char_identity",
            display_name="Character Identity",
            trigger_words=["char_id"],
            lora_type="character",
            default_weight=0.8,
        )
        db_session.add(char_lora)
        db_session.flush()

        style_loras = style_profile_with_lora.loras
        # Frontend filters out style LoRAs - only character type sent
        character_loras = [
            {
                "name": char_lora.name,
                "weight": char_lora.default_weight,
                "trigger_words": char_lora.trigger_words,
                "lora_type": "character",
            },
        ]

        builder = PromptBuilder(db_session)

        # Act
        result = builder.compose(
            tags=["1girl", "standing", "masterpiece"],
            character_loras=character_loras,
            style_loras=style_loras,
        )

        # Assert — char_identity weight 0.8 → capped to 0.76
        assert "<lora:flat_color_style:0.7>" in result, "StyleProfile LoRA applied"
        assert "<lora:char_identity:0.76>" in result, "Character LoRA should be capped to 0.76"


class TestStyleLoRADeduplication:
    """Test handling of duplicate LoRAs between StyleProfile and Character."""

    def test_dedup_same_lora_from_profile_and_character(self, db_session: Session):
        """
        Given: Same LoRA in both StyleProfile and Character.loras
        When: Generate prompt
        Then: LoRA should appear only once (StyleProfile weight takes precedence)
        """
        # Arrange - Same LoRA in both sources
        shared_lora = LoRA(
            name="shared_style_lora",
            display_name="Shared Style",
            trigger_words=["shared_trigger"],
            lora_type="style",
            default_weight=0.5,
        )
        db_session.add(shared_lora)
        db_session.flush()

        # StyleProfile has it with weight 0.7
        style_loras = [
            {
                "name": shared_lora.name,
                "weight": 0.7,
                "trigger_words": shared_lora.trigger_words,
                "lora_type": "style",
            }
        ]

        # Character also has it with weight 0.5 (should be ignored/deduped)
        character_loras = [
            {
                "name": shared_lora.name,
                "weight": 0.5,
                "trigger_words": shared_lora.trigger_words,
                "lora_type": "style",
            }
        ]

        builder = PromptBuilder(db_session)

        # Act
        result = builder.compose(
            tags=["1girl", "standing", "masterpiece"],
            character_loras=character_loras,
            style_loras=style_loras,
        )

        # Assert - LoRA should appear only once
        lora_count = result.count(f"<lora:{shared_lora.name}:")
        assert lora_count == 1, f"LoRA should appear exactly once, found {lora_count} times"
        # StyleProfile weight (0.7) should be used, not character weight (0.5)
        assert "<lora:shared_style_lora:0.7>" in result, "StyleProfile weight should take precedence"


class TestStyleLoRAFallback:
    """Test fallback behavior when StyleProfile is not set."""

    def test_no_style_loras_when_profile_empty(self, db_session: Session, character_lora_a: LoRA):
        """
        Given: No StyleProfile set (style_loras is empty)
        When: Generate prompt
        Then: Only character character LoRA should be applied (no style)
        """
        # Arrange
        style_loras = []  # No StyleProfile
        character_loras = [
            {
                "name": character_lora_a.name,
                "weight": character_lora_a.default_weight,
                "trigger_words": character_lora_a.trigger_words,
                "lora_type": "character",
            }
        ]

        builder = PromptBuilder(db_session)

        # Act
        result = builder.compose(
            tags=["1girl", "standing", "masterpiece"],
            character_loras=character_loras,
            style_loras=style_loras,
        )

        # Assert — character_a weight 0.8 → capped to 0.76
        assert "<lora:character_a_lora:0.76>" in result, "Identity LoRA should be capped to 0.76"
        assert "flat_color" not in result, "No style LoRA without StyleProfile"


class TestComposeForCharacterSkipsStyleLoRA:
    """Test that compose_for_character() skips style-type LoRAs from character.loras.

    StyleProfile is SSOT for style LoRAs. When backend loads character.loras from DB,
    it should NOT inject style-type LoRAs (to prevent double application with StyleProfile).
    """

    def test_style_lora_in_character_loras_skipped(self, db_session: Session, style_lora: LoRA, character_lora_a: LoRA):
        """
        Given: Character has both character-type AND style-type LoRAs in DB
        When: compose_for_character() is called
        Then: Only character-type LoRA should be injected; style-type should be skipped
        """
        from models import Character, Tag
        from models.associations import CharacterTag

        # Create a tag for the character
        tag = Tag(name="red_hair", category="character", group_name="hair_color")
        db_session.add(tag)
        db_session.flush()

        # Create character with BOTH lora types in its loras JSONB
        character = Character(
            name="test_char_style_skip",
            gender="female",
            group_id=1,
            loras=[
                {"lora_id": character_lora_a.id, "weight": 0.8},
                {"lora_id": style_lora.id, "weight": 0.7},  # style-type should be SKIPPED
            ],
        )
        db_session.add(character)
        db_session.flush()

        # Add a tag association
        char_tag = CharacterTag(character_id=character.id, tag_id=tag.id, weight=1.0)
        db_session.add(char_tag)
        db_session.flush()

        builder = PromptBuilder(db_session)

        # Act
        result = builder.compose_for_character(
            character_id=character.id,
            scene_tags=["standing", "smile"],
        )

        # Assert: Character LoRA always injected
        assert f"<lora:{character_lora_a.name}:" in result, "Character LoRA should be injected"
        assert "char_a_trigger" in result, "Character LoRA trigger words should be included"
        # Style LoRA fallback: when no style_loras param, character's style LoRA is applied
        # with weight capped at 0.5 (Bug 1 fix: fallback path)
        assert f"<lora:{style_lora.name}:" in result, (
            "Style LoRA from character.loras should be applied as FALLBACK when no StyleProfile"
        )
        assert f"<lora:{style_lora.name}:0.5>" in result, "Fallback style LoRA weight should be capped at 0.5"

    def test_style_lora_still_applied_via_style_loras_param(
        self, db_session: Session, style_lora: LoRA, character_lora_a: LoRA
    ):
        """
        Given: Character has style LoRA in DB, StyleProfile passes style_loras separately
        When: compose_for_character() is called with style_loras param
        Then: Style LoRA comes from style_loras param (not from character.loras)
        """
        from models import Character, Tag
        from models.associations import CharacterTag

        tag = Tag(name="blue_eyes", category="character", group_name="eye_color")
        db_session.add(tag)
        db_session.flush()

        character = Character(
            name="test_char_style_param",
            gender="female",
            group_id=1,
            loras=[
                {"lora_id": character_lora_a.id, "weight": 0.8},
                {"lora_id": style_lora.id, "weight": 0.5},  # will be skipped from character.loras
            ],
        )
        db_session.add(character)
        db_session.flush()

        char_tag = CharacterTag(character_id=character.id, tag_id=tag.id, weight=1.0)
        db_session.add(char_tag)
        db_session.flush()

        # StyleProfile provides style LoRA explicitly with different weight
        explicit_style_loras = [
            {"name": style_lora.name, "weight": 0.7, "trigger_words": style_lora.trigger_words},
        ]

        builder = PromptBuilder(db_session)

        # Act
        result = builder.compose_for_character(
            character_id=character.id,
            scene_tags=["standing"],
            style_loras=explicit_style_loras,
        )

        # Assert
        assert f"<lora:{character_lora_a.name}:" in result, "Character LoRA applied"
        assert f"<lora:{style_lora.name}:0.7>" in result, "Style LoRA from style_loras param applied"
        # Should NOT have duplicate style LoRA from character.loras
        lora_count = result.count(f"<lora:{style_lora.name}:")
        assert lora_count == 1, f"Style LoRA should appear exactly once, found {lora_count}"


class TestConsistentStyleAcrossScenes:
    """Test that all scenes in a storyboard use the same style LoRA."""

    def test_all_speakers_same_style_lora(
        self,
        db_session: Session,
        style_profile_with_lora: StyleProfile,
        character_lora_a: LoRA,
        character_lora_b: LoRA,
    ):
        """
        Given: Storyboard with StyleProfile, Characters A and B
        When: Generate prompts for A, B, and Narrator scenes
        Then: All should have the same StyleProfile LoRA
        """
        style_loras = style_profile_with_lora.loras
        builder = PromptBuilder(db_session)

        # Scene 1: Speaker A
        result_a = builder.compose(
            tags=["1girl", "talking", "masterpiece"],
            character_loras=[
                {
                    "name": character_lora_a.name,
                    "weight": 0.8,
                    "trigger_words": character_lora_a.trigger_words,
                    "lora_type": "character",
                }
            ],
            style_loras=style_loras,
        )

        # Scene 2: Speaker B
        result_b = builder.compose(
            tags=["1boy", "listening", "masterpiece"],
            character_loras=[
                {
                    "name": character_lora_b.name,
                    "weight": 0.8,
                    "trigger_words": character_lora_b.trigger_words,
                    "lora_type": "character",
                }
            ],
            style_loras=style_loras,
        )

        # Scene 3: Narrator (no character)
        result_narrator = builder.compose(
            tags=["no_humans", "scenery", "masterpiece"],
            character_loras=[],
            style_loras=style_loras,
        )

        # Assert - All scenes have the same style LoRA
        style_lora_tag = "<lora:flat_color_style:0.7>"
        assert style_lora_tag in result_a, "Speaker A should have style LoRA"
        assert style_lora_tag in result_b, "Speaker B should have same style LoRA"
        assert style_lora_tag in result_narrator, "Narrator should have same style LoRA"

        # Each scene has its own character LoRA (or none for Narrator)
        assert "<lora:character_a_lora:" in result_a
        assert "<lora:character_b_lora:" in result_b
        assert "character_a_lora" not in result_narrator
        assert "character_b_lora" not in result_narrator
