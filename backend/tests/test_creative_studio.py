"""Tests for creative_studio.py -- compose_scene_with_style integration.

_build_scene uses compose_scene_with_style (shared with Studio Direct)
for StyleProfile + V3 composition when deep_parse=True.
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


class TestBuildSceneComposition:
    """_build_scene must use compose_scene_with_style when db is provided."""

    def test_compose_scene_with_style_called(self):
        """When db provided, compose_scene_with_style must be called with correct params."""
        mock_db = MagicMock()
        style_loras = [{"name": "flat_color", "weight": 0.76}]

        with patch("services.creative_studio.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = (
                "high_quality, masterpiece, best_quality, 1girl, <lora:flat_color:0.76>",
                "lowres, bad anatomy, style_negative",
                [],
            )

            from services.creative_studio import _build_scene

            scene = _build_scene(
                s={"order": 0, "script": "Hello", "speaker": "A", "duration": 2.5, "image_prompt": "1girl, smile"},
                storyboard_id=42,
                characters={"A": {"id": 10, "name": "Haru", "tags": []}},
                fallback_char_id=None,
                style_loras=style_loras,
                db=mock_db,
            )

            mock_compose.assert_called_once()
            call_kwargs = mock_compose.call_args.kwargs
            assert call_kwargs["character_id"] == 10
            assert call_kwargs["storyboard_id"] == 42
            assert call_kwargs["style_loras"] == style_loras
            assert call_kwargs["db"] is mock_db
            assert "skip_loras" not in call_kwargs  # skip_loras is internal to compose_scene_with_style
            assert "high_quality" in scene.image_prompt
            assert "style_negative" in scene.negative_prompt

    def test_narrator_scene_passes_no_character_id(self):
        """Narrator scene (no char_id) must call compose_scene_with_style with character_id=None."""
        mock_db = MagicMock()

        with patch("services.creative_studio.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("no_humans, sunset, beach", "lowres, bad anatomy", [])

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
                characters={},
                fallback_char_id=None,
                db=mock_db,
            )

            call_kwargs = mock_compose.call_args.kwargs
            assert call_kwargs["character_id"] is None

    def test_no_db_skips_composition(self):
        """When db is None (deep_parse=False), compose_scene_with_style must not be called."""
        with patch("services.creative_studio.compose_scene_with_style") as mock_compose:
            from services.creative_studio import _build_scene

            scene = _build_scene(
                s={"order": 0, "script": "Hello", "speaker": "A", "duration": 2.5, "image_prompt": "1girl, smile"},
                storyboard_id=42,
                characters={"A": {"id": 10, "name": "Haru", "tags": []}},
                fallback_char_id=None,
            )

            mock_compose.assert_not_called()
            assert scene.image_prompt == "1girl, smile"  # raw prompt preserved

    def test_negative_prompt_is_set(self):
        """Scene must have a non-empty negative_prompt after _build_scene."""
        mock_db = MagicMock()

        with patch("services.creative_studio.compose_scene_with_style") as mock_compose:
            mock_compose.return_value = ("composed_prompt", "lowres, bad anatomy", [])

            from services.creative_studio import _build_scene

            scene = _build_scene(
                s={"order": 0, "script": "Hello", "speaker": "A", "duration": 2.5, "image_prompt": "1girl, smile"},
                storyboard_id=1,
                characters={"A": {"id": 10, "name": "Haru", "tags": []}},
                fallback_char_id=None,
                db=mock_db,
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


class TestSendToStudioDurationLanguage:
    """send_to_studio must transfer duration and language from session context."""

    def test_duration_and_language_transferred(self, db_session):
        """Storyboard must receive duration and language from session context."""
        from models import Project
        from models.group import Group
        from models.storyboard import Storyboard

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
                    "script": "Test",
                    "speaker": "A",
                    "duration": 2.5,
                    "image_prompt": "1girl, smile",
                },
            ]
        }
        session.context = {
            "structure": "Monologue",
            "duration": 10,
            "language": "English",
            "characters": None,
        }
        session.objective = "Test"
        session.character_id = None

        from services.creative_studio import send_to_studio

        result = send_to_studio(
            db=db_session,
            session=session,
            group_id=group.id,
            deep_parse=False,
        )

        sb = db_session.get(Storyboard, result["storyboard_id"])
        assert sb.duration == 10
        assert sb.language == "English"


class TestSendToStudioIntegration:
    """send_to_studio with deep_parse=True must use compose_scene_with_style."""

    def test_deep_parse_resolves_style_loras_and_composes(self, db_session):
        """When deep_parse=True, style_loras resolved and compose_scene_with_style called."""
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
            patch(
                "services.creative_studio.compose_scene_with_style",
                return_value=("composed", "negative", []),
            ) as mock_compose,
            patch(
                "services.creative_studio.resolve_style_loras_from_group",
                return_value=[{"name": "flat_color", "weight": 0.76}],
            ) as mock_lora,
        ):
            from services.creative_studio import send_to_studio

            result = send_to_studio(
                db=db_session,
                session=session,
                group_id=group.id,
                deep_parse=True,
            )

            mock_lora.assert_called_once_with(group.id, db_session)
            mock_compose.assert_called_once()
            assert result["scene_count"] == 1
