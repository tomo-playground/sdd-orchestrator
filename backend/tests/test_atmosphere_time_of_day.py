"""Atmosphere 에이전트의 time_of_day 생성/전달 테스트 (SP-117)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.agent.nodes._cine_atmosphere import _build_prompt, run_atmosphere
from services.keywords.patterns import CATEGORY_PATTERNS


class TestAtmospherePromptConstruction:
    """_build_prompt가 time_of_day 규칙을 올바르게 포함하는지 검증."""

    def test_prompt_includes_time_of_day_options(self):
        """프롬프트에 15개 time_of_day 옵션이 포함됨."""
        prompt = _build_prompt(
            scenes_json='[{"order": 0}]',
            framing_result={"scenes": []},
            action_result={"scenes": []},
            style_section="",
            writer_plan_section="",
        )
        for val in CATEGORY_PATTERNS["time_of_day"]:
            assert val in prompt, f"'{val}' should be in prompt"

    def test_prompt_includes_time_of_day_rule(self):
        """프롬프트에 'time_of_day' 규칙 섹션 포함."""
        prompt = _build_prompt(
            scenes_json='[{"order": 0}]',
            framing_result={},
            action_result={},
            style_section="",
            writer_plan_section="",
        )
        assert "time_of_day" in prompt
        assert 'Default to "day"' in prompt

    def test_prompt_output_format_includes_time_of_day(self):
        """출력 포맷 예시에 time_of_day 필드 포함."""
        prompt = _build_prompt(
            scenes_json='[{"order": 0}]',
            framing_result={},
            action_result={},
            style_section="",
            writer_plan_section="",
        )
        assert '"time_of_day": "day"' in prompt

    def test_prompt_includes_writer_plan(self):
        """writer_plan이 프롬프트에 포함되어 시간 맥락 전달됨."""
        plan = "## Writer Plan\n야근 끝나고 퇴근하는 직장인의 이야기"
        prompt = _build_prompt(
            scenes_json='[{"order": 0}]',
            framing_result={},
            action_result={},
            style_section="",
            writer_plan_section=plan,
        )
        assert "야근" in prompt


class TestAtmosphereResultPassthrough:
    """run_atmosphere가 Gemini 결과를 올바르게 전달하는지 검증."""

    @pytest.mark.asyncio
    async def test_time_of_day_in_result(self):
        """정상 응답: time_of_day 필드가 결과에 포함."""
        mock_result = {
            "scenes": [
                {
                    "order": 0,
                    "environment": ["office", "indoors"],
                    "cinematic": ["depth_of_field"],
                    "time_of_day": "night",
                }
            ]
        }
        with patch(
            "services.agent.nodes._cine_common.call_sub_agent",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await run_atmosphere(
                scenes_json='[{"order": 0}]',
                framing_result={},
                action_result={},
                style_section="",
                writer_plan_section="",
            )
        assert result is not None
        assert result["scenes"][0]["time_of_day"] == "night"

    @pytest.mark.asyncio
    async def test_missing_time_of_day_passthrough(self):
        """time_of_day 누락 응답: Atmosphere는 그대로 전달 (Finalize에서 처리)."""
        mock_result = {
            "scenes": [
                {
                    "order": 0,
                    "environment": ["park", "outdoors"],
                    "cinematic": ["sunlight"],
                }
            ]
        }
        with patch(
            "services.agent.nodes._cine_common.call_sub_agent",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await run_atmosphere(
                scenes_json='[{"order": 0}]',
                framing_result={},
                action_result={},
                style_section="",
                writer_plan_section="",
            )
        assert result is not None
        assert "time_of_day" not in result["scenes"][0]

    @pytest.mark.asyncio
    async def test_agent_failure_returns_none(self):
        """에이전트 실패 시 None 반환."""
        with patch(
            "services.agent.nodes._cine_common.call_sub_agent",
            new_callable=AsyncMock,
            side_effect=Exception("Gemini error"),
        ):
            result = await run_atmosphere(
                scenes_json='[{"order": 0}]',
                framing_result={},
                action_result={},
                style_section="",
                writer_plan_section="",
            )
        assert result is None
