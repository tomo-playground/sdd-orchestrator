"""Cinematographer 노드 — characters_tags 전달 테스트."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from services.agent.nodes.cinematographer import cinematographer_node


@pytest.mark.asyncio
@patch("services.agent.tools.base.call_with_tools", new_callable=AsyncMock)
@patch("services.agent.nodes.cinematographer.validate_visuals")
@patch("services.agent.nodes.cinematographer._try_competition", new_callable=AsyncMock, return_value=None)
async def test_characters_tags_passed_to_template(mock_comp, mock_validate, mock_call):
    """캐릭터가 있으면 characters_tags가 템플릿 render에 전달된다."""
    mock_scenes = [{"order": 0, "script": "테스트", "speaker": "A"}]
    mock_call.return_value = (
        json.dumps({"scenes": mock_scenes}),
        [],
    )
    mock_validate.return_value = {"ok": True, "issues": [], "checks": {}}

    # Character mock
    mock_char = Mock()
    mock_char.name = "TestChar"
    mock_char_tag = Mock()
    mock_char_tag.tag = Mock()
    mock_char_tag.tag.name = "brown_hair"
    mock_char_tag.tag.group_name = "hair_color"
    mock_char.tags = [mock_char_tag]
    mock_char.loras = None

    mock_db = MagicMock()
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_char
    mock_db.execute.return_value = mock_result

    state = {
        "draft_scenes": mock_scenes,
        "character_id": 1,
        "style": "Anime",
    }
    config = {"configurable": {"db": mock_db}}

    with patch("services.agent.nodes.cinematographer.template_env") as mock_tenv:
        mock_tmpl = Mock()
        mock_tmpl.render.return_value = "rendered prompt"
        mock_tenv.get_template.return_value = mock_tmpl

        await cinematographer_node(state, config)

        # render 호출 시 characters_tags 인자 확인
        call_kwargs = mock_tmpl.render.call_args
        assert "characters_tags" in call_kwargs.kwargs or (
            len(call_kwargs.args) > 0 and "characters_tags" in str(call_kwargs)
        )
        # characters_tags에 "A" 키가 있고 "brown_hair"가 identity 카테고리에 포함되어야 함
        characters_tags = call_kwargs.kwargs.get("characters_tags")
        assert characters_tags is not None
        assert "A" in characters_tags
        assert "brown_hair" in characters_tags["A"]["identity"]


@pytest.mark.asyncio
@patch("services.agent.tools.base.call_with_tools", new_callable=AsyncMock)
@patch("services.agent.nodes.cinematographer.validate_visuals")
@patch("services.agent.nodes.cinematographer._try_competition", new_callable=AsyncMock, return_value=None)
async def test_characters_tags_none_when_no_character(mock_comp, mock_validate, mock_call):
    """character_id가 없으면 characters_tags=None으로 전달된다."""
    mock_scenes = [{"order": 0, "script": "테스트"}]
    mock_call.return_value = (
        json.dumps({"scenes": mock_scenes}),
        [],
    )
    mock_validate.return_value = {"ok": True, "issues": [], "checks": {}}

    mock_db = MagicMock()
    state = {
        "draft_scenes": mock_scenes,
        "style": "Anime",
    }
    config = {"configurable": {"db": mock_db}}

    with patch("services.agent.nodes.cinematographer.template_env") as mock_tenv:
        mock_tmpl = Mock()
        mock_tmpl.render.return_value = "rendered prompt"
        mock_tenv.get_template.return_value = mock_tmpl

        await cinematographer_node(state, config)

        call_kwargs = mock_tmpl.render.call_args.kwargs
        assert call_kwargs.get("characters_tags") == {}


@pytest.mark.asyncio
@patch("services.agent.tools.base.call_with_tools", new_callable=AsyncMock)
@patch("services.agent.nodes.cinematographer.validate_visuals")
@patch("services.agent.nodes.cinematographer._try_competition", new_callable=AsyncMock, return_value=None)
async def test_characters_tags_includes_lora(mock_comp, mock_validate, mock_call):
    """캐릭터에 LoRA가 있으면 트리거 워드가 characters_tags에 포함된다."""
    mock_scenes = [{"order": 0, "script": "테스트", "speaker": "A"}]
    mock_call.return_value = (
        json.dumps({"scenes": mock_scenes}),
        [],
    )
    mock_validate.return_value = {"ok": True, "issues": [], "checks": {}}

    # Character with LoRA
    mock_char = Mock()
    mock_char.name = "LoRAChar"
    mock_char_tag = Mock()
    mock_char_tag.tag = Mock()
    mock_char_tag.tag.name = "purple_eyes"
    mock_char_tag.tag.group_name = "eye_color"
    mock_char.tags = [mock_char_tag]
    mock_char.loras = [{"lora_id": 1, "weight": 0.8}]

    # LoRA mock
    mock_lora = Mock()
    mock_lora.trigger_words = ["flat color", "Midoriya_Izuku"]

    # DB: first call → Character, second call → LoRA
    mock_db = MagicMock()
    call_count = 0

    def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = Mock()
        if call_count == 1:
            # Character query: scalar_one_or_none()
            result.scalar_one_or_none.return_value = mock_char
        else:
            # LoRA query: scalars().all()
            result.scalars.return_value.all.return_value = [mock_lora]
        return result

    mock_db.execute.side_effect = mock_execute

    state = {
        "draft_scenes": mock_scenes,
        "character_id": 1,
        "style": "Anime",
    }
    config = {"configurable": {"db": mock_db}}

    with patch("services.agent.nodes.cinematographer.template_env") as mock_tenv:
        mock_tmpl = Mock()
        mock_tmpl.render.return_value = "rendered prompt"
        mock_tenv.get_template.return_value = mock_tmpl

        await cinematographer_node(state, config)

        call_kwargs = mock_tmpl.render.call_args.kwargs
        characters_tags = call_kwargs.get("characters_tags")
        assert characters_tags is not None
        assert "A" in characters_tags
        tags_a = characters_tags["A"]
        assert "purple_eyes" in tags_a["identity"]
        assert "flat color" in tags_a["lora_triggers"]
        assert "Midoriya_Izuku" in tags_a["lora_triggers"]
