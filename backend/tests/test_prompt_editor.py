"""Tests for instruction-based prompt editing service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path):
    """All tests use isolated cache dir to prevent cross-test pollution."""
    with patch("services.prompt.prompt_editor.CACHE_DIR", tmp_path):
        yield


class TestEditBasic:
    """Basic editing functionality."""

    @patch("services.prompt.prompt_editor.gemini_client")
    def test_edit_basic(self, mock_client):
        """Gemini mock -> edited prompt returned."""
        from services.prompt.prompt_editor import edit_prompt_with_instruction

        mock_response = MagicMock()
        mock_response.text = "sitting, smile, looking_at_viewer, indoor"
        mock_client.models.generate_content.return_value = mock_response

        result = edit_prompt_with_instruction(
            current_prompt="standing, smile, looking_at_viewer, outdoor",
            instruction="앉아있는 포즈로 변경, 실내로",
        )

        assert "edited_prompt" in result
        assert "sitting" in result["edited_prompt"]

    @patch("services.prompt.prompt_editor.gemini_client")
    def test_edit_preserves_structure(self, mock_client):
        """Tag order/structure preserved for unrelated tags."""
        from services.prompt.prompt_editor import edit_prompt_with_instruction

        mock_response = MagicMock()
        mock_response.text = "cowboy_shot, closed_eyes, looking_at_viewer, park"
        mock_client.models.generate_content.return_value = mock_response

        result = edit_prompt_with_instruction(
            current_prompt="cowboy_shot, smile, looking_at_viewer, park",
            instruction="눈 감기",
        )

        assert result["edited_prompt"] == "cowboy_shot, closed_eyes, looking_at_viewer, park"

    @patch("services.prompt.prompt_editor.gemini_client")
    def test_edit_strips_backticks(self, mock_client):
        """Gemini response backtick cleanup."""
        from services.prompt.prompt_editor import edit_prompt_with_instruction

        mock_response = MagicMock()
        mock_response.text = "```sitting, smile```"
        mock_client.models.generate_content.return_value = mock_response

        result = edit_prompt_with_instruction(
            current_prompt="standing, smile",
            instruction="앉기",
        )
        assert "```" not in result["edited_prompt"]


class TestEditWithCharacter:
    """Character context integration."""

    @patch("services.prompt.prompt_editor.gemini_client")
    def test_edit_with_character_context(self, mock_client):
        """character_id provided -> exclude tags included."""
        from services.prompt.prompt_editor import edit_prompt_with_instruction

        mock_response = MagicMock()
        mock_response.text = "sitting, cafe, warm_lighting"
        mock_client.models.generate_content.return_value = mock_response

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [("brown_hair",), ("blue_eyes",)]

        result = edit_prompt_with_instruction(
            current_prompt="standing, park, sunny",
            instruction="카페에서 앉기",
            character_id=1,
            db=mock_db,
        )

        assert result["edited_prompt"] == "sitting, cafe, warm_lighting"
        call_args = mock_client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents", "")
        assert "brown_hair" in contents
        assert "blue_eyes" in contents


class TestEditCache:
    """Caching behavior."""

    @patch("services.prompt.prompt_editor.gemini_client")
    def test_cache_hit(self, mock_client):
        """Same input returns cached result."""
        from services.prompt.prompt_editor import edit_prompt_with_instruction

        mock_response = MagicMock()
        mock_response.text = "sitting, smile"
        mock_client.models.generate_content.return_value = mock_response

        result1 = edit_prompt_with_instruction(
            current_prompt="standing, smile",
            instruction="앉기",
        )
        assert mock_client.models.generate_content.call_count == 1

        result2 = edit_prompt_with_instruction(
            current_prompt="standing, smile",
            instruction="앉기",
        )
        assert mock_client.models.generate_content.call_count == 1
        assert result1 == result2


class TestEditErrors:
    """Error handling."""

    def test_no_gemini_client(self):
        """gemini_client=None -> 503."""
        from services.prompt.prompt_editor import edit_prompt_with_instruction

        with patch("services.prompt.prompt_editor.gemini_client", None):
            with pytest.raises(HTTPException) as exc_info:
                edit_prompt_with_instruction(
                    current_prompt="test",
                    instruction="change",
                )
            assert exc_info.value.status_code == 503

    def test_empty_input(self):
        """Empty inputs -> 400."""
        from services.prompt.prompt_editor import edit_prompt_with_instruction

        with patch("services.prompt.prompt_editor.gemini_client", MagicMock()):
            with pytest.raises(HTTPException) as exc_info:
                edit_prompt_with_instruction(current_prompt="", instruction="change")
            assert exc_info.value.status_code == 400

            with pytest.raises(HTTPException) as exc_info:
                edit_prompt_with_instruction(current_prompt="tags", instruction="")
            assert exc_info.value.status_code == 400

            with pytest.raises(HTTPException) as exc_info:
                edit_prompt_with_instruction(current_prompt="   ", instruction="change")
            assert exc_info.value.status_code == 400


class TestEditEndpoint:
    """API endpoint integration test."""

    @patch("services.prompt.prompt_editor.gemini_client")
    def test_endpoint_integration(self, mock_client):
        """/edit-prompt API integration test."""
        mock_response = MagicMock()
        mock_response.text = "sitting, smile, indoor"
        mock_client.models.generate_content.return_value = mock_response

        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)
        resp = client.post(
            "/api/admin/prompt/edit-prompt",
            json={
                "current_prompt": "standing, smile, outdoor",
                "instruction": "앉아있는 포즈로, 실내로",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "edited_prompt" in data
        assert "sitting" in data["edited_prompt"]
