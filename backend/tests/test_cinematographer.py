"""Cinematographer 노드 JSON 파싱 방어 + graceful degradation 테스트."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.nodes.cinematographer import _parse_scenes, _run

# call_with_tools는 lazy import이므로 원본 모듈을 패치
_CWT = "services.agent.tools.base.call_with_tools"
_QC = "services.agent.nodes.cinematographer.validate_visuals"


def _make_state(scenes: list | None = None, skip_stages: list | None = None) -> dict:
    """테스트용 ScriptState 생성."""
    return {
        "draft_scenes": scenes or [{"order": 1, "text": "test", "duration": 3.0}],
        "character_id": None,
        "director_feedback": None,
        "skip_stages": skip_stages if skip_stages is not None else ["research", "concept", "production", "explain"],
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


# ── 빈 응답 / 설명 텍스트 혼재 방어 테스트 ──────────────────


def test_parse_scenes_empty_string():
    """빈 문자열 → None (json.JSONDecodeError 방지)."""
    assert _parse_scenes("") is None


def test_parse_scenes_whitespace_only():
    """공백만 있는 응답 → None."""
    assert _parse_scenes("   \n\t  ") is None


def test_parse_scenes_preamble_then_json():
    """설명 텍스트 뒤에 JSON이 이어지는 경우 → 전략 3으로 추출."""
    body = json.dumps({"scenes": [{"order": 1, "text": "test"}]})
    response = f"알겠습니다. 각 씬에 비주얼 디자인을 추가하겠습니다.\n\n{body}"
    result = _parse_scenes(response)
    assert result == [{"order": 1, "text": "test"}]


def test_parse_scenes_tool_explanation_no_json():
    """도구 사용 설명만 반환하고 JSON 없는 경우 → None."""
    response = (
        "validate_danbooru_tag 도구로 brown_hair를 검증했습니다. "
        "이 태그는 유효합니다. 다음으로 카메라 앵글을 검토하겠습니다."
    )
    assert _parse_scenes(response) is None


def test_parse_scenes_raw_json_no_codeblock():
    """코드블록 없이 raw JSON만 반환되는 경우."""
    body = json.dumps({"scenes": [{"order": 1, "camera": "close-up"}]})
    assert _parse_scenes(body) == [{"order": 1, "camera": "close-up"}]


def test_parse_scenes_json_with_trailing_text():
    """JSON 뒤에 설명 텍스트가 붙는 경우 → 전략 3으로 추출."""
    body = json.dumps({"scenes": [{"order": 1}]})
    response = f"결과:\n{body}\n\n이상 비주얼 디자인입니다."
    result = _parse_scenes(response)
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


# ── Phase 11-P3: visual_qc_result state 저장 ─────────────────


@pytest.mark.asyncio
async def test_visual_qc_result_stored_in_state():
    """QC 결과가 visual_qc_result로 state에 저장된다."""
    valid = json.dumps({"scenes": [{"order": 1, "visual_tags": ["brown_hair"]}]})
    qc_result = {"ok": False, "issues": ["camera diversity low"], "checks": {"camera_diversity": "WARN"}}
    with patch(_CWT, new_callable=AsyncMock, return_value=(f"```json\n{valid}\n```", [])):
        with patch(_QC, return_value=qc_result):
            result = await _run(_make_state(), MagicMock())
    assert "visual_qc_result" in result
    assert result["visual_qc_result"] == qc_result
    assert result["visual_qc_result"]["ok"] is False
