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
@patch("services.agent.langfuse_prompt.compile_prompt")
async def test_characters_tags_passed_to_template(mock_compile, mock_comp, mock_validate, mock_call):
    """캐릭터가 있으면 characters_tags_block이 compile_prompt에 전달된다."""
    mock_compile.return_value = MagicMock(system="sys", user="rendered prompt", langfuse_prompt=None)
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

    await cinematographer_node(state, config)

    # compile_prompt 호출 시 characters_tags_block이 비어있지 않아야 함 (캐릭터 존재)
    compile_kwargs = mock_compile.call_args.kwargs
    assert "characters_tags_block" in compile_kwargs
    block = compile_kwargs["characters_tags_block"]
    assert "Speaker" in block
    assert block != ""


@pytest.mark.asyncio
@patch("services.agent.tools.base.call_with_tools", new_callable=AsyncMock)
@patch("services.agent.nodes.cinematographer.validate_visuals")
@patch("services.agent.nodes.cinematographer._try_competition", new_callable=AsyncMock, return_value=None)
@patch("services.agent.langfuse_prompt.compile_prompt")
async def test_characters_tags_none_when_no_character(mock_compile, mock_comp, mock_validate, mock_call):
    """character_id가 없으면 characters_tags_block이 빈 상태로 전달된다."""
    mock_compile.return_value = MagicMock(system="sys", user="rendered prompt", langfuse_prompt=None)
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

    await cinematographer_node(state, config)

    compile_kwargs = mock_compile.call_args.kwargs
    # 캐릭터 없으면 characters_tags_block은 빈 문자열
    assert compile_kwargs.get("characters_tags_block") == ""


def test_load_single_character_tags_includes_lora():
    """_load_single_character_tags가 LoRA 트리거 워드를 lora_triggers에 포함한다."""
    from services.agent.nodes.cinematographer import _load_single_character_tags

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

    # DB mock: first call → Character, second call → LoRA
    mock_db = MagicMock()
    call_count = 0

    def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = Mock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = mock_char
        else:
            result.scalars.return_value.all.return_value = [mock_lora]
        return result

    mock_db.execute.side_effect = mock_execute

    tags = _load_single_character_tags(1, mock_db)

    assert "purple_eyes" in tags["identity"]
    assert "flat color" in tags["lora_triggers"]
    assert "Midoriya_Izuku" in tags["lora_triggers"]
