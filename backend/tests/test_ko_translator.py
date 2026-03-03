"""Tests for KO → EN prompt translation service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path):
    """All tests use isolated cache dir to prevent cross-test pollution."""
    with patch("services.prompt.ko_translator.CACHE_DIR", tmp_path):
        yield


class TestTranslateKoBasic:
    """Basic translation functionality."""

    @patch("services.prompt.ko_translator.gemini_client")
    def test_translate_ko_basic(self, mock_client):
        """Gemini mock → 태그 반환."""
        from services.prompt.ko_translator import translate_ko_to_prompt

        mock_response = MagicMock()
        mock_response.text = "cowboy_shot, smile, looking_at_viewer, park, sunny"
        mock_client.models.generate_content.return_value = mock_response

        result = translate_ko_to_prompt(ko_text="공원에서 미소짓는 소녀")

        assert "translated_prompt" in result
        assert "source_ko" in result
        assert result["source_ko"] == "공원에서 미소짓는 소녀"
        assert "cowboy_shot" in result["translated_prompt"]

    @patch("services.prompt.ko_translator.gemini_client")
    def test_translate_ko_with_current_prompt(self, mock_client):
        """현재 프롬프트 참조 동작."""
        from services.prompt.ko_translator import translate_ko_to_prompt

        mock_response = MagicMock()
        mock_response.text = "running, wind, outdoor"
        mock_client.models.generate_content.return_value = mock_response

        result = translate_ko_to_prompt(
            ko_text="바람 속에서 달리는 장면",
            current_prompt="cowboy_shot, smile",
        )

        assert result["translated_prompt"] == "running, wind, outdoor"
        # Verify current_prompt was included in the instruction
        call_args = mock_client.models.generate_content.call_args
        assert "cowboy_shot, smile" in call_args.kwargs.get("contents", "")

    @patch("services.prompt.ko_translator.gemini_client")
    def test_translate_ko_strips_backticks(self, mock_client):
        """Gemini 응답의 backtick 제거."""
        from services.prompt.ko_translator import translate_ko_to_prompt

        mock_response = MagicMock()
        mock_response.text = "```cowboy_shot, smile```"
        mock_client.models.generate_content.return_value = mock_response

        result = translate_ko_to_prompt(ko_text="미소짓는 소녀")
        assert "```" not in result["translated_prompt"]


class TestTranslateKoWithCharacter:
    """Character context integration."""

    @patch("services.prompt.ko_translator.gemini_client")
    def test_translate_ko_with_character_context(self, mock_client):
        """character_id 제공 시 제외 태그 포함."""
        from services.prompt.ko_translator import translate_ko_to_prompt

        mock_response = MagicMock()
        mock_response.text = "sitting, cafe, warm_lighting"
        mock_client.models.generate_content.return_value = mock_response

        # Mock DB session with character tags
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [("brown_hair",), ("blue_eyes",)]

        result = translate_ko_to_prompt(
            ko_text="카페에서 앉아있는 장면",
            character_id=1,
            db=mock_db,
        )

        assert result["translated_prompt"] == "sitting, cafe, warm_lighting"
        # Verify exclude section was included
        call_args = mock_client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents", "")
        assert "brown_hair" in contents
        assert "blue_eyes" in contents


class TestTranslateKoCache:
    """Caching behavior."""

    @patch("services.prompt.ko_translator.gemini_client")
    def test_translate_ko_cache_hit(self, mock_client):
        """동일 입력 캐시 반환."""
        from services.prompt.ko_translator import translate_ko_to_prompt

        mock_response = MagicMock()
        mock_response.text = "smile, happy"
        mock_client.models.generate_content.return_value = mock_response

        # First call — hits Gemini
        result1 = translate_ko_to_prompt(ko_text="행복한 미소")
        assert mock_client.models.generate_content.call_count == 1

        # Second call — cache hit
        result2 = translate_ko_to_prompt(ko_text="행복한 미소")
        assert mock_client.models.generate_content.call_count == 1
        assert result1 == result2


class TestTranslateKoErrors:
    """Error handling."""

    def test_translate_ko_no_gemini_client(self):
        """gemini_client=None → 503."""
        from services.prompt.ko_translator import translate_ko_to_prompt

        with patch("services.prompt.ko_translator.gemini_client", None):
            with pytest.raises(HTTPException) as exc_info:
                translate_ko_to_prompt(ko_text="테스트")
            assert exc_info.value.status_code == 503

    def test_translate_ko_empty_input(self):
        """빈 입력 → 400."""
        from services.prompt.ko_translator import translate_ko_to_prompt

        with patch("services.prompt.ko_translator.gemini_client", MagicMock()):
            with pytest.raises(HTTPException) as exc_info:
                translate_ko_to_prompt(ko_text="")
            assert exc_info.value.status_code == 400

            with pytest.raises(HTTPException) as exc_info:
                translate_ko_to_prompt(ko_text="   ")
            assert exc_info.value.status_code == 400


class TestTranslateKoEndpoint:
    """API endpoint integration test."""

    @patch("services.prompt.ko_translator.gemini_client")
    def test_translate_ko_endpoint(self, mock_client):
        """/translate-ko API 통합 테스트."""
        mock_response = MagicMock()
        mock_response.text = "cowboy_shot, smile"
        mock_client.models.generate_content.return_value = mock_response

        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)
        resp = client.post(
            "/api/v1/prompt/translate-ko",
            json={"ko_text": "미소짓는 소녀"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "translated_prompt" in data
        assert "source_ko" in data
        assert data["source_ko"] == "미소짓는 소녀"
