"""Cinematographer 노드 JSON 파싱 방어 + graceful degradation 테스트."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.nodes.cinematographer import _parse_scenes, _run

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


# ── _parse_scenes 단위 테스트 ─────────────────────────────────


def test_parse_scenes_valid_json():
    """정상 JSON dict → scenes 리스트 반환."""
    body = json.dumps({"scenes": [{"order": 1}]})
    assert _parse_scenes(f"```json\n{body}\n```") == [{"order": 1}]


def test_parse_scenes_string_response():
    """json.loads가 string → None."""
    assert _parse_scenes('"just a string"') is None


def test_parse_scenes_list_response():
    """json.loads가 list → None."""
    assert _parse_scenes("[1, 2, 3]") is None


def test_parse_scenes_number_response():
    """json.loads가 number → None."""
    assert _parse_scenes("42") is None


def test_parse_scenes_invalid_json():
    """유효하지 않은 JSON → None."""
    assert _parse_scenes("not json {{{") is None


def test_parse_scenes_no_scenes_key():
    """scenes 키 없는 dict → 빈 리스트."""
    assert _parse_scenes('{"data": "x"}') == []


def test_parse_scenes_markdown_codeblock():
    """```json 코드블록 정상 추출."""
    body = json.dumps({"scenes": [{"order": 1}]})
    result = _parse_scenes(f"Here:\n```json\n{body}\n```\nDone.")
    assert result == [{"order": 1}]


# ── Graceful degradation (error를 설정하지 않음) ─────────────


@pytest.mark.asyncio
async def test_valid_json_returns_result():
    """정상 JSON → cinematographer_result 반환, error 없음."""
    valid = json.dumps(
        {
            "scenes": [
                {"order": 1, "text": "t", "visual_tags": ["brown_hair"], "camera": "close-up", "environment": "indoors"}
            ]
        }
    )
    with patch(_CWT, new_callable=AsyncMock, return_value=(f"```json\n{valid}\n```", [])):
        with patch(_QC, return_value={"ok": True, "issues": [], "checks": {}}):
            result = await _run(_make_state(), MagicMock())
    assert "error" not in result
    assert result["cinematographer_result"]["scenes"][0]["visual_tags"] == ["brown_hair"]


@pytest.mark.asyncio
async def test_json_parse_failure_no_error():
    """JSON 파싱 실패 → error 미설정, cinematographer_result=None."""
    with patch(_CWT, new_callable=AsyncMock, return_value=("not json {{{", [])):
        result = await _run(_make_state(), MagicMock())
    assert "error" not in result
    assert result["cinematographer_result"] is None
    assert result["cinematographer_tool_logs"] == []


@pytest.mark.asyncio
async def test_non_dict_response_no_error():
    """json.loads가 non-dict → error 미설정, cinematographer_result=None."""
    with patch(_CWT, new_callable=AsyncMock, return_value=('"just a string"', [])):
        result = await _run(_make_state(), MagicMock())
    assert "error" not in result
    assert result["cinematographer_result"] is None


@pytest.mark.asyncio
async def test_tool_calling_exception_no_error():
    """call_with_tools 예외 → error 미설정, graceful fallback."""
    with patch(_CWT, new_callable=AsyncMock, side_effect=RuntimeError("Gemini not init")):
        result = await _run(_make_state(), MagicMock())
    assert "error" not in result
    assert result["cinematographer_result"] is None
    assert result["cinematographer_tool_logs"] == []


@pytest.mark.asyncio
async def test_qc_failure_still_returns_result():
    """QC FAIL → error 미설정, 결과는 그대로 반환 (graceful)."""
    valid = json.dumps({"scenes": [{"order": 1}]})
    with patch(_CWT, new_callable=AsyncMock, return_value=(f"```json\n{valid}\n```", [])):
        with patch(
            _QC, return_value={"ok": False, "issues": ["missing tags"], "checks": {"image_prompt_present": "FAIL"}}
        ):
            result = await _run(_make_state(), MagicMock())
    assert "error" not in result
    assert result["cinematographer_result"] is not None
    assert result["cinematographer_result"]["scenes"] == [{"order": 1}]


@pytest.mark.asyncio
async def test_tool_logs_preserved_on_parse_failure():
    """JSON 파싱 실패 시에도 tool_logs 보존."""
    logs = [{"tool_name": "validate_danbooru_tag", "arguments": {"tag": "test"}, "result": "ok", "error": None}]
    with patch(_CWT, new_callable=AsyncMock, return_value=("not json", logs)):
        result = await _run(_make_state(), MagicMock())
    assert result["cinematographer_tool_logs"] == logs


@pytest.mark.asyncio
async def test_empty_scenes_key():
    """scenes 키 없는 dict → 빈 scenes으로 정상 반환."""
    with patch(_CWT, new_callable=AsyncMock, return_value=('{"data": "x"}', [])):
        with patch(_QC, return_value={"ok": True, "issues": [], "checks": {}}):
            result = await _run(_make_state(), MagicMock())
    assert result["cinematographer_result"]["scenes"] == []
