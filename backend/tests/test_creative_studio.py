"""Tests for creative_studio.py -- V3 composition + negative prompt integration.

BLOCKER #1: _build_scene must use V3 composition pipeline, not raw V3Builder.
"""

from unittest.mock import MagicMock, patch


def _make_session_context(characters=None, character_id=None):
    """Helper to build a minimal CreativeSession-like object."""
    session = MagicMock()
    session.final_output = {
        "scenes": [
            {
                "order": 0,
                "script": "Test script",
                "speaker": "A",
                "duration": 2.5,
                "image_prompt": "1girl, smile, classroom",
            },
        ]
    }
    session.context = {
        "structure": "Monologue",
        "characters": characters or {},
    }
    session.objective = "Test objective"
    session.character_id = character_id
    return session


class TestBuildSceneWithStyleLoras:
    """_build_scene must pass style_loras to V3 composition."""

    def test_actor_scene_passes_style_loras(self):
        """Actor scene (char_id present) must pass style_loras to compose_for_character."""
        mock_builder = MagicMock()
        mock_builder.compose_for_character.return_value = "composed_prompt"

        from services.creative_studio import _build_scene

        _build_scene(
            s={
                "order": 0,
                "script": "Hello",
                "speaker": "A",
                "duration": 2.5,
                "image_prompt": "1girl, smile",
            },
            storyboard_id=1,
            builder=mock_builder,
            characters={"A": {"id": 10, "name": "Haru", "tags": []}},
            fallback_char_id=None,
            group_id=1,
        )

        # Must pass style_loras kwarg
        call_kwargs = mock_builder.compose_for_character.call_args
        assert "style_loras" in call_kwargs.kwargs, "compose_for_character must receive style_loras"

    def test_narrator_scene_uses_compose(self):
        """Narrator scene (no char_id, no_humans) must use builder.compose."""
        mock_builder = MagicMock()
        mock_builder.compose_for_character.return_value = "composed"
        mock_builder.compose.return_value = "bg_prompt"

        from services.creative_studio import _build_scene

        _build_scene(
            s={
                "order": 0,
                "script": "Scenery",
                "speaker": "Narrator",
                "duration": 2.5,
                "image_prompt": "no_humans, sunset, beach",
            },
            storyboard_id=1,
            builder=mock_builder,
            characters={},
            fallback_char_id=None,
            group_id=1,
        )

        # No characters → should use compose (not compose_for_character)
        mock_builder.compose.assert_called_once()


class TestBuildSceneNegativePrompt:
    """_build_scene must set negative_prompt on the Scene."""

    def test_negative_prompt_is_set(self):
        """Scene must have a non-empty negative_prompt after _build_scene."""
        mock_builder = MagicMock()
        mock_builder.compose_for_character.return_value = "composed"

        from services.creative_studio import _build_scene

        scene = _build_scene(
            s={
                "order": 0,
                "script": "Hello",
                "speaker": "A",
                "duration": 2.5,
                "image_prompt": "1girl, smile",
            },
            storyboard_id=1,
            builder=mock_builder,
            characters={"A": {"id": 10, "name": "Haru", "tags": []}},
            fallback_char_id=None,
            group_id=1,
        )

        assert scene.negative_prompt, "Scene.negative_prompt must not be empty"


class TestSendToStudioNullCharacters:
    """send_to_studio must handle None characters in session context."""

    def test_null_characters_does_not_crash(self, db_session):
        """ctx['characters'] = None must not raise AttributeError."""
        from models import Project
        from models.group import Group

        project = Project(name="Test")
        db_session.add(project)
        db_session.flush()
        group = Group(name="G", project_id=project.id)
        db_session.add(group)
        db_session.flush()

        # Simulate session where characters is explicitly None
        session = MagicMock()
        session.final_output = {
            "scenes": [
                {
                    "order": 0,
                    "script": "Solo narration",
                    "speaker": "A",
                    "duration": 2.5,
                    "image_prompt": "1girl, classroom",
                },
            ]
        }
        session.context = {"structure": "Monologue", "characters": None}
        session.objective = "Test"
        session.character_id = None

        from services.creative_studio import send_to_studio

        result = send_to_studio(
            db=db_session,
            session=session,
            group_id=group.id,
            deep_parse=False,
        )

        assert result["scene_count"] == 1

    def test_missing_characters_key_does_not_crash(self, db_session):
        """ctx with no 'characters' key must not raise."""
        from models import Project
        from models.group import Group

        project = Project(name="Test")
        db_session.add(project)
        db_session.flush()
        group = Group(name="G", project_id=project.id)
        db_session.add(group)
        db_session.flush()

        session = MagicMock()
        session.final_output = {
            "scenes": [
                {
                    "order": 0,
                    "script": "Solo",
                    "speaker": "A",
                    "duration": 2.5,
                    "image_prompt": "1girl, smile",
                },
            ]
        }
        session.context = {"structure": "Monologue"}  # no characters key
        session.objective = "Test"
        session.character_id = None

        from services.creative_studio import send_to_studio

        result = send_to_studio(
            db=db_session,
            session=session,
            group_id=group.id,
            deep_parse=False,
        )

        assert result["scene_count"] == 1


class TestMonologueCharacterLinkage:
    """Monologue session with character_id must create StoryboardCharacter."""

    def test_monologue_links_fallback_character(self, db_session):
        """session.character_id (monologue) must create StoryboardCharacter for speaker A."""
        from models import Project
        from models.character import Character
        from models.group import Group
        from models.storyboard_character import StoryboardCharacter

        project = Project(name="Test")
        db_session.add(project)
        db_session.flush()
        group = Group(name="G", project_id=project.id)
        db_session.add(group)
        db_session.flush()
        char = Character(name="Haru")
        db_session.add(char)
        db_session.flush()

        # Monologue: character_id set, but characters dict is None
        session = MagicMock()
        session.final_output = {
            "scenes": [
                {
                    "order": 0,
                    "script": "Hello",
                    "speaker": "A",
                    "duration": 2.5,
                    "image_prompt": "1girl, smile",
                },
            ]
        }
        session.context = {"structure": "Monologue", "characters": None}
        session.objective = "Test"
        session.character_id = char.id

        from services.creative_studio import send_to_studio

        result = send_to_studio(
            db=db_session,
            session=session,
            group_id=group.id,
            deep_parse=False,
        )

        # StoryboardCharacter must exist for speaker A
        sc = db_session.query(StoryboardCharacter).filter_by(storyboard_id=result["storyboard_id"], speaker="A").first()
        assert sc is not None, "StoryboardCharacter must be created for monologue"
        assert sc.character_id == char.id

    def test_no_character_id_no_link(self, db_session):
        """No character_id and no characters dict → no StoryboardCharacter."""
        from models import Project
        from models.group import Group
        from models.storyboard_character import StoryboardCharacter

        project = Project(name="Test")
        db_session.add(project)
        db_session.flush()
        group = Group(name="G", project_id=project.id)
        db_session.add(group)
        db_session.flush()

        session = MagicMock()
        session.final_output = {
            "scenes": [
                {
                    "order": 0,
                    "script": "Narration",
                    "speaker": "A",
                    "duration": 2.5,
                    "image_prompt": "no_humans, sunset",
                },
            ]
        }
        session.context = {"structure": "Monologue", "characters": None}
        session.objective = "Test"
        session.character_id = None

        from services.creative_studio import send_to_studio

        result = send_to_studio(
            db=db_session,
            session=session,
            group_id=group.id,
            deep_parse=False,
        )

        sc_count = db_session.query(StoryboardCharacter).filter_by(storyboard_id=result["storyboard_id"]).count()
        assert sc_count == 0, "No character → no StoryboardCharacter"


class TestSendToStudioIntegration:
    """send_to_studio with deep_parse=True must use full V3 pipeline."""

    def test_deep_parse_creates_builder_with_style_loras(self, db_session):
        """When deep_parse=True, V3Builder is created and style_loras resolved."""
        from models import Project
        from models.character import Character
        from models.group import Group

        project = Project(name="Test")
        db_session.add(project)
        db_session.flush()
        group = Group(name="G", project_id=project.id)
        db_session.add(group)
        db_session.flush()
        char = Character(name="Haru")
        db_session.add(char)
        db_session.flush()

        session = _make_session_context(
            characters={"A": {"id": char.id, "name": "Haru", "tags": []}},
            character_id=char.id,
        )

        with (
            patch("services.prompt.v3_composition.V3PromptBuilder") as MockBuilder,
            patch(
                "services.creative_studio.resolve_style_loras_from_group",
                return_value=[],
            ) as mock_lora,
        ):
            mock_instance = MagicMock()
            mock_instance.compose_for_character.return_value = "composed"
            mock_instance.compose.return_value = "composed"
            MockBuilder.return_value = mock_instance

            from services.creative_studio import send_to_studio

            result = send_to_studio(
                db=db_session,
                session=session,
                group_id=group.id,
                deep_parse=True,
            )

            mock_lora.assert_called_once_with(group.id, db_session)
            assert result["scene_count"] == 1
