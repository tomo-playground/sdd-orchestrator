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
    """Quick 모드에서 compile_prompt() 경유 system instruction이 사용된다."""
    mock_preset = MockPreset()

    mock_raw = MagicMock()
    mock_raw.text = '[\n  {\n    "scene_id": 1,\n    "script": "Hello",\n    "image_prompt": "1girl, solo",\n    "speaker": "A"\n  }\n]'
    mock_raw.prompt_feedback = None
    mock_raw.candidates = []
    mock_llm_response = MagicMock()
    mock_llm_response.text = mock_raw.text
    mock_llm_response.raw = mock_raw

    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_llm_response)

    # compile_prompt 반환값 mock
    mock_compiled = MagicMock()
    mock_compiled.system = "You are a professional storyboarder and scriptwriter"
    mock_compiled.user = "Rendered Template Content"
    mock_compiled.langfuse_prompt = None

    with patch("services.script.gemini_generator.get_preset_by_structure", return_value=mock_preset):
        with patch("services.agent.langfuse_prompt.compile_prompt", return_value=mock_compiled):
            with patch("services.llm.get_llm_provider", return_value=mock_provider):
                request = MockRequest()
                await generate_script(request, db=mock_db)

                assert mock_provider.generate.called
                kwargs = mock_provider.generate.call_args.kwargs
                # system_instruction은 LLMConfig에 분리되어 전달됨
                config = kwargs.get("config")
                assert config is not None
                assert "You are a professional storyboarder and scriptwriter" in config.system_instruction
