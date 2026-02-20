"""gemini_generator Quick 모드 system_instruction 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.script.gemini_generator import generate_script


class MockRequest:
    def __init__(
        self,
        structure="monologue",
        character_id=1,
        character_b_id=None,
        topic="Topic",
        description="Desc",
        duration=30,
        style="anime",
        language="Korean",
        actor_a_gender="female",
        selected_concept=None,
        group_id=None,
    ):
        self.structure = structure
        self.character_id = character_id
        self.character_b_id = character_b_id
        self.topic = topic
        self.description = description
        self.duration = duration
        self.style = style
        self.language = language
        self.actor_a_gender = actor_a_gender
        self.selected_concept = selected_concept
        self.group_id = group_id


class MockPreset:
    def __init__(self, template="create_storyboard.j2", extra_fields=None):
        self.template = template
        self.extra_fields = extra_fields or {}


@pytest.fixture
def mock_gemini_client():
    with patch("services.script.gemini_generator.gemini_client") as mock_client:
        mock_response = AsyncMock()
        mock_response.text = '[\n  {\n    "scene_id": 1,\n    "script": "Hello",\n    "image_prompt": "1girl, solo",\n    "speaker": "A"\n  }\n]'
        mock_response.prompt_feedback = None
        mock_response.candidates = []

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        yield mock_client


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value.options.return_value.filter.return_value.first.return_value = None
    yield db


@pytest.mark.asyncio
async def test_generate_script_uses_fallback_system_prompt(mock_gemini_client, mock_db):
    """Quick 모드에서 fallback system instruction이 사용된다."""
    mock_preset = MockPreset()

    with patch("services.script.gemini_generator.get_preset_by_structure", return_value=mock_preset):
        with patch("services.script.gemini_generator.template_env.get_template") as mock_get_template:
            mock_template = MagicMock()
            mock_template.render.return_value = "Rendered Template Content"
            mock_get_template.return_value = mock_template

            with patch("services.script.gemini_generator._call_gemini_with_retry", new_callable=AsyncMock) as mock_call:
                mock_response = AsyncMock()
                mock_response.text = '[\n  {\n    "scene_id": 1,\n    "script": "Hello",\n    "image_prompt": "1girl, solo",\n    "speaker": "A"\n  }\n]'
                mock_call.return_value = mock_response

                request = MockRequest()
                await generate_script(request, db=mock_db)

                assert mock_call.called
                kwargs = mock_call.call_args.kwargs
                contents = kwargs.get("contents")
                assert "SYSTEM: You are a professional storyboarder and scriptwriter" in contents
