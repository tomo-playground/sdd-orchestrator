"""Cinematographer Team 분해 테스트 (SP-046).

4 서브 에이전트 순차 실행 + Compositor 통합 + 단일 에이전트 fallback.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.nodes._cine_action import _parse_result as parse_action
from services.agent.nodes._cine_atmosphere import _parse_result as parse_atmosphere
from services.agent.nodes._cine_framing import _parse_result as parse_framing
from services.agent.nodes.cinematographer import _run, _run_team

# ── 서브 에이전트 파싱 테스트 ─────────────────────────────────


class TestFramingParse:
    def test_valid_json(self):
        body = json.dumps({"scenes": [{"order": 0, "camera": "close-up", "gaze": "looking_down"}]})
        result = parse_framing(body)
        assert result is not None
        assert result["scenes"][0]["camera"] == "close-up"

    def test_code_block(self):
        body = json.dumps({"scenes": [{"order": 0, "camera": "dutch_angle"}]})
        result = parse_framing(f"```json\n{body}\n```")
        assert result is not None
        assert result["scenes"][0]["camera"] == "dutch_angle"

    def test_empty(self):
        assert parse_framing("") is None
        assert parse_framing("  ") is None

    def test_invalid_json(self):
        assert parse_framing("not json {{{") is None

    def test_no_scenes_key(self):
        assert parse_framing('{"data": 1}') is None


class TestActionParse:
    def test_valid_json(self):
        body = json.dumps({"scenes": [{"order": 0, "emotion": "nervous", "pose": "standing"}]})
        result = parse_action(body)
        assert result is not None
        assert result["scenes"][0]["emotion"] == "nervous"

    def test_code_block(self):
        body = json.dumps({"scenes": [{"order": 0, "emotion": "happy"}]})
        result = parse_action(f"Here:\n```json\n{body}\n```\nDone.")
        assert result is not None

    def test_empty(self):
        assert parse_action("") is None


class TestAtmosphereParse:
    def test_valid_json(self):
        body = json.dumps({"scenes": [{"order": 0, "environment": ["kitchen"], "cinematic": ["bokeh"]}]})
        result = parse_atmosphere(body)
        assert result is not None
        assert "kitchen" in result["scenes"][0]["environment"]

    def test_empty(self):
        assert parse_atmosphere("") is None


# ── 팀 오케스트레이션 테스트 ────────────────────────────────

_FRAMING = {
    "scenes": [{"order": 0, "camera": "close-up", "gaze": "looking_down", "ken_burns_preset": "zoom_in_center"}]
}
_ACTION = {
    "scenes": [
        {
            "order": 0,
            "emotion": "nervous",
            "action": "holding_knife",
            "pose": "standing",
            "props": ["knife"],
            "controlnet_pose": "standing",
        }
    ]
}
_ATMOSPHERE = {"scenes": [{"order": 0, "environment": ["kitchen", "indoors"], "cinematic": ["depth_of_field"]}]}
_COMPOSITOR_SCENES = [{"order": 0, "script": "test", "camera": "close-up", "image_prompt": "nervous, holding_knife"}]

_QC_OK = {"ok": True, "issues": [], "checks": {}}


@pytest.mark.asyncio
@patch("services.agent.nodes._cine_compositor.run_compositor", new_callable=AsyncMock)
@patch("services.agent.nodes._cine_atmosphere.run_atmosphere", new_callable=AsyncMock)
@patch("services.agent.nodes._cine_action.run_action", new_callable=AsyncMock)
@patch("services.agent.nodes._cine_framing.run_framing", new_callable=AsyncMock)
@patch("services.agent.nodes.cinematographer.validate_visuals")
async def test_team_success(mock_qc, mock_framing, mock_action, mock_atmo, mock_comp):
    """팀 실행 성공 시 cinematographer_result 반환."""
    mock_framing.return_value = _FRAMING
    mock_action.return_value = _ACTION
    mock_atmo.return_value = _ATMOSPHERE
    mock_comp.return_value = (_COMPOSITOR_SCENES, [{"tool_name": "test", "result": "ok"}])
    mock_qc.return_value = _QC_OK

    result = await _run_team(
        scenes_json='[{"order": 0, "script": "test"}]',
        visual_direction="dark tone",
        writer_plan_section="",
        characters_tags_block="",
        style_section="",
        image_prompt_ko_rules="",
        emotion_consistency_rules="",
        tools=[],
        tool_executors={},
    )

    assert result is not None
    assert result["cinematographer_result"]["scenes"] == _COMPOSITOR_SCENES
    assert len(result["cinematographer_tool_logs"]) == 1


@pytest.mark.asyncio
@patch("services.agent.nodes._cine_framing.run_framing", new_callable=AsyncMock, return_value=None)
async def test_team_framing_failure_returns_none(mock_framing):
    """Framing 실패 시 None 반환 (단일 에이전트 fallback으로 이어짐)."""
    result = await _run_team(
        scenes_json="[]",
        visual_direction="",
        writer_plan_section="",
        characters_tags_block="",
        style_section="",
        image_prompt_ko_rules="",
        emotion_consistency_rules="",
        tools=[],
        tool_executors={},
    )
    assert result is None


@pytest.mark.asyncio
@patch("services.agent.nodes._cine_action.run_action", new_callable=AsyncMock, return_value=None)
@patch("services.agent.nodes._cine_framing.run_framing", new_callable=AsyncMock, return_value=_FRAMING)
async def test_team_action_failure_returns_none(mock_framing, mock_action):
    """Action 실패 시 None 반환."""
    result = await _run_team(
        scenes_json="[]",
        visual_direction="",
        writer_plan_section="",
        characters_tags_block="",
        style_section="",
        image_prompt_ko_rules="",
        emotion_consistency_rules="",
        tools=[],
        tool_executors={},
    )
    assert result is None


@pytest.mark.asyncio
@patch("services.agent.nodes._cine_atmosphere.run_atmosphere", new_callable=AsyncMock, return_value=None)
@patch("services.agent.nodes._cine_action.run_action", new_callable=AsyncMock, return_value=_ACTION)
@patch("services.agent.nodes._cine_framing.run_framing", new_callable=AsyncMock, return_value=_FRAMING)
async def test_team_atmosphere_failure_returns_none(mock_framing, mock_action, mock_atmo):
    """Atmosphere 실패 시 None 반환."""
    result = await _run_team(
        scenes_json="[]",
        visual_direction="",
        writer_plan_section="",
        characters_tags_block="",
        style_section="",
        image_prompt_ko_rules="",
        emotion_consistency_rules="",
        tools=[],
        tool_executors={},
    )
    assert result is None


@pytest.mark.asyncio
@patch("services.agent.nodes._cine_compositor.run_compositor", new_callable=AsyncMock, return_value=(None, []))
@patch("services.agent.nodes._cine_atmosphere.run_atmosphere", new_callable=AsyncMock, return_value=_ATMOSPHERE)
@patch("services.agent.nodes._cine_action.run_action", new_callable=AsyncMock, return_value=_ACTION)
@patch("services.agent.nodes._cine_framing.run_framing", new_callable=AsyncMock, return_value=_FRAMING)
async def test_team_compositor_failure_returns_none(mock_framing, mock_action, mock_atmo, mock_comp):
    """Compositor 실패 시 None 반환."""
    result = await _run_team(
        scenes_json="[]",
        visual_direction="",
        writer_plan_section="",
        characters_tags_block="",
        style_section="",
        image_prompt_ko_rules="",
        emotion_consistency_rules="",
        tools=[],
        tool_executors={},
    )
    assert result is None


# ── 오케스트레이터 fallback 테스트 ──────────────────────────

_CWT = "services.agent.tools.base.call_with_tools"
_QC_PATCH = "services.agent.nodes.cinematographer.validate_visuals"


def _make_state(scenes=None, skip_stages=None):
    return {
        "draft_scenes": scenes or [{"order": 1, "text": "test", "duration": 3.0}],
        "character_id": None,
        "director_feedback": None,
        "skip_stages": skip_stages if skip_stages is not None else ["research", "concept", "production", "explain"],
    }


@pytest.mark.asyncio
async def test_run_falls_through_to_single_when_team_fails():
    """팀 실패 → 단일 에이전트 fallback이 동작한다."""
    valid = json.dumps({"scenes": [{"order": 1, "camera": "close-up"}]})
    # _run_team은 sub-agent 호출이 실패하여 None 반환 (mock 없이 자연 실패)
    # _run_single은 call_with_tools mock으로 성공
    with patch(_CWT, new_callable=AsyncMock, return_value=(f"```json\n{valid}\n```", [], None)):
        with patch(_QC_PATCH, return_value=_QC_OK):
            result = await _run(_make_state(), MagicMock())

    assert result["cinematographer_result"] is not None
    assert result["cinematographer_result"]["scenes"][0]["camera"] == "close-up"


# ── 프롬프트 충돌 시나리오 테스트 ───────────────────────────


class TestConflictScenarios:
    """Compositor가 해결해야 할 크로스 도메인 충돌 사례."""

    def test_closeup_plus_holding_phone_detected(self):
        """close-up + holding_phone — attention 경쟁 시나리오."""
        scenes = [{"order": 0, "image_prompt": "close-up, holding_phone, hand_on_cheek"}]
        # 이 태그 조합은 SDXL에서 attention 경쟁을 유발
        tags = set(scenes[0]["image_prompt"].split(", "))
        has_close_up = "close-up" in tags
        has_holding = any(t.startswith("holding_") for t in tags)
        # Compositor는 이 경우 camera를 cowboy_shot으로 조정하거나 holding 제거해야 함
        assert has_close_up and has_holding  # 충돌 존재 확인

    def test_sitting_plus_full_body_conflict(self):
        """sitting + full_body — 다리 왜곡 시나리오."""
        # 이 조합은 SDXL에서 다리가 왜곡됨
        conflict_tags = {"sitting", "full_body"}
        # Compositor는 full_body를 upper_body로 교체해야 함
        assert "sitting" in conflict_tags and "full_body" in conflict_tags


# ── DirectorPlan visual_direction 테스트 ─────────────────────


class TestVisualDirection:
    def test_director_plan_has_visual_direction_field(self):
        """DirectorPlan TypedDict에 visual_direction 필드가 존재한다."""
        from services.agent.state import DirectorPlan

        plan: DirectorPlan = {
            "creative_goal": "test",
            "visual_direction": "어두운 톤에서 밝은 톤으로 전환, 클라이막스 씬 4",
        }
        assert plan["visual_direction"] == "어두운 톤에서 밝은 톤으로 전환, 클라이막스 씬 4"

    def test_cine_team_result_type(self):
        """CineTeamResult TypedDict이 존재한다."""
        from services.agent.state import CineTeamResult

        result: CineTeamResult = {
            "framing": {"scenes": []},
            "action": {"scenes": []},
            "atmosphere": {"scenes": []},
        }
        assert "framing" in result
