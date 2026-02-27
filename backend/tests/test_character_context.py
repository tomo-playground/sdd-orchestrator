"""Tests for character identity injection into storyboard generation.

Covers:
- _load_character_context: tag classification by layer, LoRA trigger extraction
- StoryboardRequest: character_id field acceptance
- Jinja2 template: character_context block rendering
"""

from unittest.mock import MagicMock

from schemas import StoryboardRequest
from services.storyboard import _load_character_context

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_tag(name: str, default_layer: int, tag_id: int = 1):
    """Build a mock Tag object."""
    tag = MagicMock()
    tag.name = name
    tag.default_layer = default_layer
    tag.id = tag_id
    return tag


def _make_character_tag(tag_name: str, default_layer: int, tag_id: int = 1):
    """Build a mock CharacterTag with nested Tag."""
    ct = MagicMock()
    ct.tag = _make_tag(tag_name, default_layer, tag_id)
    return ct


def _make_character(
    char_id: int = 1,
    name: str = "TestChar",
    gender: str = "female",
    tags: list | None = None,
    loras: list | None = None,
    custom_base_prompt: str = "",
):
    """Build a mock Character object."""
    char = MagicMock()
    char.id = char_id
    char.name = name
    char.gender = gender
    char.tags = tags or []
    char.loras = loras
    char.custom_base_prompt = custom_base_prompt
    return char


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

        char = Character(name="NoTags", gender="male")
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result is not None
        assert result["name"] == "NoTags"
        assert result["gender"] == "male"
        assert result["identity_tags"] == []
        assert result["costume_tags"] == []
        assert result["lora_triggers"] == []
        assert result["custom_base_prompt"] == ""

    def test_identity_tags_layer_0_to_3(self, db_session):
        """Tags with default_layer 0-3 are classified as identity."""
        from models.associations import CharacterTag
        from models.character import Character
        from models.tag import Tag

        char = Character(name="IdentityTest", gender="female")
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

        char = Character(name="CostumeTest", gender="female")
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

        char = Character(name="MixedTest", gender="female")
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
            loras=[{"lora_id": 99999, "weight": 0.5}],
        )
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result["lora_triggers"] == []

    def test_custom_base_prompt(self, db_session):
        """custom_base_prompt is included in context."""
        from models.character import Character

        char = Character(
            name="PromptTest",
            gender="male",
            custom_base_prompt="1boy, solo, detailed_eyes",
        )
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result["custom_base_prompt"] == "1boy, solo, detailed_eyes"

    def test_gender_defaults_to_female(self, db_session):
        """If gender is None, defaults to 'female'."""
        from models.character import Character

        char = Character(name="NoGender")
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result["gender"] == "female"

    def test_description_included(self, db_session):
        """description 필드가 컨텍스트에 포함된다."""
        from models.character import Character

        char = Character(name="WithDesc", gender="male", description="활발한 남학생")
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result["description"] == "활발한 남학생"

    def test_description_none_defaults_empty(self, db_session):
        """description이 None이면 빈 문자열."""
        from models.character import Character

        char = Character(name="NoDesc", gender="female")
        db_session.add(char)
        db_session.commit()

        result = _load_character_context(char.id, db_session)
        assert result["description"] == ""


# ---------------------------------------------------------------------------
# Jinja2 template rendering
# ---------------------------------------------------------------------------


class TestTemplateCharacterContext:
    """Test that create_storyboard.j2 renders character_context block."""

    def test_template_without_character_context(self):
        """Template renders normally without character_context."""
        from config import template_env

        template = template_env.get_template("create_storyboard.j2")
        rendered = template.render(
            topic="test",
            description="",
            duration=10,
            style="Anime",
            structure="Monologue",
            language="Korean",
            actor_a_gender="female",
            keyword_context="",
            character_context=None,
        )
        assert "FIXED CHARACTER IDENTITY" not in rendered

    def test_template_with_character_context(self):
        """Template renders character identity block when context provided."""
        from config import template_env

        template = template_env.get_template("create_storyboard.j2")
        ctx = {
            "name": "Sakura",
            "gender": "female",
            "identity_tags": ["pink_hair", "green_eyes"],
            "costume_tags": ["school_uniform", "red_ribbon"],
            "lora_triggers": ["sakura_trigger"],
            "custom_base_prompt": "",
        }
        rendered = template.render(
            topic="test",
            description="",
            duration=10,
            style="Anime",
            structure="Monologue",
            language="Korean",
            actor_a_gender="female",
            keyword_context="",
            character_context=ctx,
        )
        assert "FIXED CHARACTER IDENTITY" in rendered
        assert "Sakura" in rendered
        assert "pink_hair, green_eyes" in rendered
        assert "school_uniform, red_ribbon" in rendered
        assert "sakura_trigger" in rendered
        assert "CHARACTER CONSISTENCY RULES" in rendered

    def test_template_omits_empty_sections(self):
        """Template omits identity/costume/lora sections when empty."""
        from config import template_env

        template = template_env.get_template("create_storyboard.j2")
        ctx = {
            "name": "Plain",
            "gender": "male",
            "description": "",
            "identity_tags": [],
            "costume_tags": [],
            "lora_triggers": [],
            "custom_base_prompt": "",
        }
        rendered = template.render(
            topic="test",
            description="",
            duration=10,
            style="Anime",
            structure="Monologue",
            language="Korean",
            actor_a_gender="male",
            keyword_context="",
            character_context=ctx,
        )
        assert "FIXED CHARACTER IDENTITY" in rendered
        assert "Plain" in rendered
        # Header lines for tag sections should not appear when lists are empty
        assert "Identity Tags (hair, eyes, body" not in rendered
        assert "Costume Tags (clothing, accessories" not in rendered
        assert "LoRA Trigger Words (MUST include" not in rendered
        assert "Personality/Background" not in rendered

    def test_template_renders_description_and_script_rules(self):
        """Template renders description and SCRIPT RULES when provided."""
        from config import template_env

        template = template_env.get_template("create_storyboard.j2")
        ctx = {
            "name": "미도리",
            "gender": "male",
            "description": "활발한 남학생, 장난끼가 있다",
            "identity_tags": ["green_hair"],
            "costume_tags": [],
            "lora_triggers": [],
            "custom_base_prompt": "",
        }
        rendered = template.render(
            topic="test",
            description="",
            duration=10,
            style="Anime",
            structure="Monologue",
            language="Korean",
            actor_a_gender="male",
            keyword_context="",
            character_context=ctx,
        )
        assert "Personality/Background: 활발한 남학생, 장난끼가 있다" in rendered
        assert "SCRIPT RULES for 미도리" in rendered
        assert "matches male character" in rendered
        assert "활발한 남학생, 장난끼가 있다" in rendered

    def test_dialogue_template_renders_both_characters(self):
        """Dialogue template renders both Speaker A and B with profiles."""
        from config import template_env

        template = template_env.get_template("create_storyboard_dialogue.j2")
        ctx_a = {
            "name": "미도리",
            "gender": "male",
            "description": "활발한 남학생",
            "identity_tags": ["green_hair"],
            "costume_tags": [],
            "lora_triggers": [],
        }
        ctx_b = {
            "name": "유카리",
            "gender": "female",
            "description": "차분한 여학생",
            "identity_tags": ["purple_hair"],
            "costume_tags": [],
            "lora_triggers": [],
        }
        rendered = template.render(
            topic="test",
            description="",
            duration=30,
            style="Anime",
            language="Korean",
            character_context=ctx_a,
            character_b_context=ctx_b,
        )
        assert "SPEAKER A - FIXED CHARACTER IDENTITY" in rendered
        assert "SPEAKER B - FIXED CHARACTER IDENTITY" in rendered
        assert "미도리" in rendered
        assert "유카리" in rendered
        assert "활발한 남학생" in rendered
        assert "차분한 여학생" in rendered
        assert "matches male character" in rendered
        assert "matches female character" in rendered
