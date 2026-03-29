"""location_planner 노드 단위 테스트.

대본(draft_scenes) 분석 기반 위치 배정 테스트.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.nodes.location_planner import (
    _build_scenes_block,
    location_planner_node,
)
from services.agent.state import build_director_context

# ---------------------------------------------------------------------------
# _build_scenes_block
# ---------------------------------------------------------------------------


class TestBuildScenesBlock:
    def test_basic(self):
        scenes = [
            {"script": "첫 출근 날"},
            {"script": "회사 법카로"},
        ]
        result = _build_scenes_block(scenes)
        assert "Scene 0: 첫 출근 날" in result
        assert "Scene 1: 회사 법카로" in result

    def test_empty_script(self):
        scenes = [{"script": ""}, {"script": "내용 있음"}]
        result = _build_scenes_block(scenes)
        assert "Scene 0" not in result
        assert "Scene 1: 내용 있음" in result

    def test_empty_scenes(self):
        assert _build_scenes_block([]) == ""


# ---------------------------------------------------------------------------
# _build_director_context
# ---------------------------------------------------------------------------


class TestBuildDirectorContext:
    def test_no_director_plan(self):
        assert build_director_context({}) is None  # type: ignore[arg-type]

    def test_builds_context_string(self):
        state = {
            "director_plan": {
                "creative_goal": "감동 전달",
                "target_emotion": "여운",
                "quality_criteria": ["진정성", "몰입감"],
            }
        }
        result = build_director_context(state)  # type: ignore[arg-type]
        assert result is not None
        assert "감동 전달" in result
        assert "여운" in result
        assert "진정성" in result


# ---------------------------------------------------------------------------
# location_planner_node
# ---------------------------------------------------------------------------


@pytest.fixture()
def state_with_scripts():
    return {
        "topic": "첫 출근 날",
        "description": "새 회사 첫날 이야기",
        "duration": 30,
        "language": "korean",
        "structure": "monologue",
        "draft_scenes": [
            {"script": "첫 출근 날, 설레는 마음으로"},
            {"script": "회사 법카로 간식 플렉스"},
            {"script": "알람은 왜 안 울려!"},
            {"script": "지하철 반대로 탔어"},
            {"script": "편의점에서 당 보충"},
        ],
    }


@pytest.fixture()
def state_without_scripts():
    return {
        "topic": "테스트",
        "duration": 10,
    }


class TestLocationPlannerNode:
    @pytest.mark.asyncio()
    async def test_no_draft_scenes_returns_empty(self, state_without_scripts):
        """draft_scenes 없으면 빈 dict 반환."""
        result = await location_planner_node(state_without_scripts)
        assert result == {}

    @pytest.mark.asyncio()
    async def test_successful_location_planning(self, state_with_scripts):
        """정상 케이스: 대본 분석 후 writer_plan.locations 설정."""
        mock_llm_resp = MagicMock()
        mock_llm_resp.text = (
            '{"locations": ['
            '{"name": "office", "scenes": [0, 1], "tags": ["office", "indoors"]},'
            '{"name": "bedroom", "scenes": [2], "tags": ["bedroom", "indoors"]},'
            '{"name": "subway", "scenes": [3], "tags": ["train_interior", "indoors"]},'
            '{"name": "convenience_store", "scenes": [4], "tags": ["convenience_store", "indoors"]}'
            "]}"
        )
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_llm_resp)

        with patch("services.agent.nodes.location_planner.get_llm_provider", return_value=mock_provider):
            result = await location_planner_node(state_with_scripts)

        assert "writer_plan" in result
        locs = result["writer_plan"]["locations"]
        assert len(locs) == 4
        assert locs[0]["name"] == "office"

    @pytest.mark.asyncio()
    async def test_preserves_existing_writer_plan(self, state_with_scripts):
        """기존 writer_plan 필드를 보존하면서 locations를 추가/갱신한다."""
        state_with_scripts["writer_plan"] = {"hook_strategy": "기존 훅", "emotional_arc": ["기대", "감동"]}

        mock_llm_resp = MagicMock()
        mock_llm_resp.text = (
            '{"locations": [{"name": "kitchen", "scenes": [0, 1, 2, 3, 4], "tags": ["kitchen", "indoors"]}]}'
        )
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_llm_resp)

        with patch("services.agent.nodes.location_planner.get_llm_provider", return_value=mock_provider):
            result = await location_planner_node(state_with_scripts)

        wp = result["writer_plan"]
        assert wp["hook_strategy"] == "기존 훅"
        assert wp["locations"][0]["name"] == "kitchen"

    @pytest.mark.asyncio()
    async def test_llm_failure_returns_empty(self, state_with_scripts):
        """LLM 호출 실패 시 빈 dict 반환 (graceful degradation)."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=Exception("API error"))

        with patch("services.agent.nodes.location_planner.get_llm_provider", return_value=mock_provider):
            result = await location_planner_node(state_with_scripts)

        assert result == {}

    @pytest.mark.asyncio()
    async def test_empty_locations_returns_empty(self, state_with_scripts):
        """빈 locations 응답 시 빈 dict 반환."""
        mock_llm_resp = MagicMock()
        mock_llm_resp.text = '{"locations": []}'
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_llm_resp)

        with patch("services.agent.nodes.location_planner.get_llm_provider", return_value=mock_provider):
            result = await location_planner_node(state_with_scripts)

        assert result == {}

    @pytest.mark.asyncio()
    async def test_scenes_block_passed_to_llm(self, state_with_scripts):
        """LLM에 실제 대본 내용이 전달되는지 확인."""
        mock_llm_resp = MagicMock()
        mock_llm_resp.text = '{"locations": [{"name": "office", "scenes": [0], "tags": ["office", "indoors"]}]}'
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_llm_resp)

        with patch("services.agent.nodes.location_planner.get_llm_provider", return_value=mock_provider):
            await location_planner_node(state_with_scripts)

        call_args = mock_provider.generate.call_args
        user_content = call_args.kwargs.get("contents", "") or call_args[1].get("contents", "")
        assert "첫 출근 날" in user_content
        assert "편의점에서 당 보충" in user_content
