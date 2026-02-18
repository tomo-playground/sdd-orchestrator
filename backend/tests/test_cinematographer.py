"""Cinematographer 노드 JSON 파싱 방어 테스트."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.nodes.cinematographer import _run

# call_with_tools는 lazy import이므로 원본 모듈을 패치
_CWT = "services.agent.tools.base.call_with_tools"
_QC = "services.agent.nodes.cinematographer.validate_visuals"


def _make_state(scenes: list | None = None) -> dict:
    """테스트용 ScriptState 생성."""
    return {
        "draft_scenes": scenes or [{"order": 1, "text": "test", "duration": 3.0}],
        "character_id": None,
        "director_feedback": None,
        "mode": "full",
    }


# ── JSON 파싱 방어 ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_json_dict():
    """정상 JSON dict → cinematographer_result 반환."""
    valid = json.dumps({"scenes": [{"order": 1, "text": "t", "visual_tags": ["brown_hair"], "camera": "close-up", "environment": "indoors"}]})
    with patch(_CWT, new_callable=AsyncMock, return_value=(f"```json\n{valid}\n```", [])):
        with patch(_QC, return_value={"valid": True}):
            result = await _run(_make_state(), MagicMock())
    assert "cinematographer_result" in result
    assert result["cinematographer_result"]["scenes"][0]["visual_tags"] == ["brown_hair"]


@pytest.mark.asyncio
async def test_json_returns_string():
    """json.loads가 string 반환 → error + 'Expected dict'."""
    with patch(_CWT, new_callable=AsyncMock, return_value=('"just a string"', [])):
        result = await _run(_make_state(), MagicMock())
    assert "error" in result
    assert "Expected dict" in result["error"]


@pytest.mark.asyncio
async def test_json_returns_list():
    """json.loads가 list 반환 → error + 'Expected dict'."""
    with patch(_CWT, new_callable=AsyncMock, return_value=("[1, 2, 3]", [])):
        result = await _run(_make_state(), MagicMock())
    assert "error" in result
    assert "Expected dict" in result["error"]


@pytest.mark.asyncio
async def test_json_returns_number():
    """json.loads가 number 반환 → error + 'Expected dict'."""
    with patch(_CWT, new_callable=AsyncMock, return_value=("42", [])):
        result = await _run(_make_state(), MagicMock())
    assert "error" in result
    assert "Expected dict" in result["error"]


@pytest.mark.asyncio
async def test_invalid_json():
    """유효하지 않은 JSON → JSONDecodeError."""
    with patch(_CWT, new_callable=AsyncMock, return_value=("not json {{{", [])):
        result = await _run(_make_state(), MagicMock())
    assert "error" in result
    assert "JSON parsing failed" in result["error"]


@pytest.mark.asyncio
async def test_json_without_scenes_key():
    """scenes 키 없는 dict → 빈 scenes."""
    with patch(_CWT, new_callable=AsyncMock, return_value=('{"data": "x"}', [])):
        with patch(_QC, return_value={"valid": True}):
            result = await _run(_make_state(), MagicMock())
    assert "cinematographer_result" in result
    assert result["cinematographer_result"]["scenes"] == []


@pytest.mark.asyncio
async def test_json_in_markdown_codeblock():
    """```json 코드블록 정상 추출."""
    body = json.dumps({"scenes": [{"order": 1, "text": "t", "visual_tags": [], "camera": "w", "environment": "o"}]})
    with patch(_CWT, new_callable=AsyncMock, return_value=(f"Here:\n```json\n{body}\n```\nDone.", [])):
        with patch(_QC, return_value={"valid": True}):
            result = await _run(_make_state(), MagicMock())
    assert "cinematographer_result" in result
    assert len(result["cinematographer_result"]["scenes"]) == 1


@pytest.mark.asyncio
async def test_qc_validation_failure():
    """QC 검증 실패 → error 반환."""
    valid = json.dumps({"scenes": [{"order": 1}]})
    with patch(_CWT, new_callable=AsyncMock, return_value=(f"```json\n{valid}\n```", [])):
        with patch(_QC, return_value={"valid": False, "errors": ["missing tags"]}):
            result = await _run(_make_state(), MagicMock())
    assert "error" in result
    assert "Visual QC failed" in result["error"]


@pytest.mark.asyncio
async def test_tool_calling_exception():
    """call_with_tools 예외 → error 반환 + tool_logs 빈 리스트."""
    with patch(_CWT, new_callable=AsyncMock, side_effect=RuntimeError("Gemini not init")):
        result = await _run(_make_state(), MagicMock())
    assert "error" in result
    assert "Cinematographer failed" in result["error"]
    assert result["cinematographer_tool_logs"] == []


@pytest.mark.asyncio
async def test_error_preserves_tool_logs():
    """JSON 파싱 실패 시에도 tool_logs 보존."""
    logs = [{"tool_name": "validate_danbooru_tag", "arguments": {"tag": "test"}, "result": "ok", "error": None}]
    with patch(_CWT, new_callable=AsyncMock, return_value=("not json", logs)):
        result = await _run(_make_state(), MagicMock())
    assert "error" in result
    assert result["cinematographer_tool_logs"] == logs
