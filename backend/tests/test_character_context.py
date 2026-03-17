"""Tests for character identity injection into storyboard generation.

Covers:
- _load_character_context: tag classification by layer, LoRA trigger extraction
- StoryboardRequest: character_id field acceptance
"""

from schemas import StoryboardRequest
from services.storyboard import _load_character_context

# ---------------------------------------------------------------------------
# StoryboardRequest schema
# ---------------------------------------------------------------------------


class TestStoryboardRequestCharacterId:
    """character_id field on StoryboardRequest."""

    def test_default_none(self):
        req = StoryboardRequest(topic="test")
        assert req.character_id is None

    def test_accepts_integer(self):
        req = StoryboardRequest(topic="test", character_id=42)
        assert req.character_id == 42

    def test_serialization(self):
        req = StoryboardRequest(topic="test", character_id=7)
        data = req.model_dump()
        assert data["character_id"] == 7


# ---------------------------------------------------------------------------
# _load_character_context
# ---------------------------------------------------------------------------


class TestLoadCharacterContext:
    """Tests for _load_character_context function."""

    def test_character_not_found_returns_none(self, db_session):
        result = _load_character_context(99999, db_session)
        assert result is None

    def test_basic_character_no_tags(self, db_session):
        """Character with no tags returns empty tag lists."""
        from models.character import Character

        char = Character(name="NoTags", gender="male", group_id=1)
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result is not None
        assert result["name"] == "NoTags"
        assert result["gender"] == "male"
        assert result["identity_tags"] == []
        assert result["costume_tags"] == []
        assert result["lora_triggers"] == []
        assert result["positive_prompt"] == ""

    def test_identity_tags_layer_0_to_3(self, db_session):
        """Tags with default_layer 0-3 are classified as identity."""
        from models.associations import CharacterTag
        from models.character import Character
        from models.tag import Tag

        char = Character(name="IdentityTest", gender="female", group_id=1)
        db_session.add(char)
        db_session.flush()

        for layer, tag_name in [(0, "masterpiece"), (1, "1girl"), (2, "brown_hair"), (3, "brown_eyes")]:
            tag = Tag(name=tag_name, default_layer=layer)
            db_session.add(tag)
            db_session.flush()
            ct = CharacterTag(character_id=char.id, tag_id=tag.id)
            db_session.add(ct)

        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert "masterpiece" in result["identity_tags"]
        assert "1girl" in result["identity_tags"]
        assert "brown_hair" in result["identity_tags"]
        assert "brown_eyes" in result["identity_tags"]
        assert result["costume_tags"] == []

    def test_costume_tags_layer_4_to_6(self, db_session):
        """Tags with default_layer 4-6 are classified as costume."""
        from models.associations import CharacterTag
        from models.character import Character
        from models.tag import Tag

        char = Character(name="CostumeTest", gender="female", group_id=1)
        db_session.add(char)
        db_session.flush()

        for layer, tag_name in [(4, "school_uniform"), (5, "red_ribbon"), (6, "backpack")]:
            tag = Tag(name=tag_name, default_layer=layer)
            db_session.add(tag)
            db_session.flush()
            ct = CharacterTag(character_id=char.id, tag_id=tag.id)
            db_session.add(ct)

        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result["identity_tags"] == []
        assert "school_uniform" in result["costume_tags"]
        assert "red_ribbon" in result["costume_tags"]
        assert "backpack" in result["costume_tags"]

    def test_mixed_layers(self, db_session):
        """Tags are correctly split between identity and costume."""
        from models.associations import CharacterTag
        from models.character import Character
        from models.tag import Tag

        char = Character(name="MixedTest", gender="female", group_id=1)
        db_session.add(char)
        db_session.flush()

        tags_data = [
            (2, "blonde_hair"),
            (3, "blue_eyes"),
            (4, "sailor_uniform"),
            (5, "white_socks"),
            (7, "smile"),  # layer 7 = expression, neither identity nor costume
        ]
        for layer, tag_name in tags_data:
            tag = Tag(name=tag_name, default_layer=layer)
            db_session.add(tag)
            db_session.flush()
            ct = CharacterTag(character_id=char.id, tag_id=tag.id)
            db_session.add(ct)

        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert set(result["identity_tags"]) == {"blonde_hair", "blue_eyes"}
        assert set(result["costume_tags"]) == {"sailor_uniform", "white_socks"}
        # "smile" (layer 7) should not appear in either list
        assert "smile" not in result["identity_tags"]
        assert "smile" not in result["costume_tags"]

    def test_lora_trigger_words(self, db_session):
        """LoRA trigger words are extracted from linked LoRA records."""
        from models.character import Character
        from models.lora import LoRA

        lora = LoRA(name="test_lora", trigger_words=["trigger_a", "trigger_b"])
        db_session.add(lora)
        db_session.flush()

        char = Character(
            name="LoRATest",
            gender="female",
            group_id=1,
            loras=[{"lora_id": lora.id, "weight": 0.8}],
        )
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert "trigger_a" in result["lora_triggers"]
        assert "trigger_b" in result["lora_triggers"]

    def test_lora_missing_in_db(self, db_session):
        """LoRA reference with nonexistent ID is safely skipped."""
        from models.character import Character

        char = Character(
            name="MissingLoRA",
            gender="female",
            group_id=1,
            loras=[{"lora_id": 99999, "weight": 0.5}],
        )
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result["lora_triggers"] == []

    def test_positive_prompt(self, db_session):
        """positive_prompt is included in context."""
        from models.character import Character

        char = Character(
            name="PromptTest",
            gender="male",
            group_id=1,
            positive_prompt="1boy, solo, detailed_eyes",
        )
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result["positive_prompt"] == "1boy, solo, detailed_eyes"

    def test_gender_defaults_to_female(self, db_session):
        """If gender is None, defaults to 'female'."""
        from models.character import Character

        char = Character(name="NoGender", group_id=1)
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result["gender"] == "female"

    def test_description_included(self, db_session):
        """description 필드가 컨텍스트에 포함된다."""
        from models.character import Character

        char = Character(name="WithDesc", gender="male", group_id=1, description="활발한 남학생")
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result["description"] == "활발한 남학생"

    def test_description_none_defaults_empty(self, db_session):
        """description이 None이면 빈 문자열."""
        from models.character import Character

        char = Character(name="NoDesc", gender="female", group_id=1)
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result["description"] == ""
