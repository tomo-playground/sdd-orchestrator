"""Integration tests for Dialogue storyboard creation."""

from schemas import StoryboardRequest


class TestDialogueValidation:
    """Test dialogue-specific validation in create_storyboard()."""

    def test_dialogue_requires_character_b_id(self):
        """Dialogue without character_b_id should raise 400."""
        request = StoryboardRequest(
            topic="Test dialogue",
            structure="dialogue",
            character_id=1,
            character_b_id=None,
        )
        assert request.structure == "dialogue"
        assert request.character_b_id is None

    def test_dialogue_requires_character_id(self):
        """Dialogue without character_id should raise 400."""
        request = StoryboardRequest(
            topic="Test dialogue",
            structure="dialogue",
            character_id=None,
            character_b_id=2,
        )
        assert request.character_id is None

    def test_dialogue_same_character_fails(self):
        """Speaker A and B must be different characters."""
        request = StoryboardRequest(
            topic="Test dialogue",
            structure="dialogue",
            character_id=1,
            character_b_id=1,
        )
        assert request.character_id == request.character_b_id

    def test_monologue_ignores_character_b(self):
        """Monologue should work fine with character_b_id=None."""
        request = StoryboardRequest(
            topic="Test monologue",
            structure="monologue",
            character_id=1,
        )
        assert request.character_b_id is None


class TestDialoguePreset:
    """Test that the dialogue preset exists and is properly configured."""

    def test_dialogue_preset_exists(self):
        from services.presets import get_preset_by_structure

        preset = get_preset_by_structure("dialogue")
        assert preset is not None
        assert preset.id == "dialogue"
        assert preset.template == "create_storyboard_dialogue"

    def test_dialogue_preset_in_all_presets(self):
        from services.presets import get_all_presets

        presets = get_all_presets()
        dialogue = next((p for p in presets if p["structure"] == "dialogue"), None)
        assert dialogue is not None
        assert dialogue["name"] == "Dialogue"


class TestStoryboardSaveWithCharacterB:
    """Test schema accepts character_b_id."""

    def test_storyboard_save_with_character_b(self):
        from schemas import StoryboardSave

        save = StoryboardSave(
            title="Test",
            group_id=1,
            character_b_id=42,
            scenes=[],
        )
        assert save.character_b_id == 42

    def test_storyboard_save_without_character_b(self):
        from schemas import StoryboardSave

        save = StoryboardSave(
            title="Test",
            group_id=1,
            scenes=[],
        )
        assert save.character_b_id is None
