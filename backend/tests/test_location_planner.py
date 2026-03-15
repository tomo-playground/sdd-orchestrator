"""location_planner 노드 단위 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.nodes.location_planner import (
    _estimate_scene_range,
    location_planner_node,
)
from services.agent.state import build_director_context

# ---------------------------------------------------------------------------
# _estimate_scene_range
# ---------------------------------------------------------------------------


class TestEstimateSceneRange:
    def test_10s_video(self):
        mn, mx = _estimate_scene_range(10)
        assert mn == 3
        assert mx == 5

    def test_15s_video(self):
        mn, mx = _estimate_scene_range(15)
        assert mn == 5
        assert mx == 8

    def test_minimum_floor(self):
        mn, _ = _estimate_scene_range(5)
        assert mn >= 1

    def test_dialogue_45s(self):
        mn, mx = _estimate_scene_range(45, "Dialogue")
        assert mn == 8
        assert mx == 12

    def test_dialogue_45s_vs_monologue_45s(self):
        """Dialogue should produce fewer scenes than Monologue for same duration."""
        d_mn, d_mx = _estimate_scene_range(45, "Dialogue")
        m_mn, m_mx = _estimate_scene_range(45, "Monologue")
        assert d_mx < m_mx

    def test_max_ge_min(self):
        for dur in [5, 10, 15, 20, 30]:
            mn, mx = _estimate_scene_range(dur)
            assert mx >= mn


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
def full_state():
    return {
        "topic": "첫 번째 칼",
        "description": "요리사의 이야기",
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
        "skip_stages": [],
    }


@pytest.fixture()
def quick_state():
    return {
        "topic": "테스트",
        "duration": 10,
        "skip_stages": ["concept"],
    }


class TestLocationPlannerNode:
    @pytest.mark.asyncio()
    async def test_quick_mode_skips(self, quick_state):
        """Quick 모드(concept 스킵)에서는 노드가 빈 dict 반환."""
        result = await location_planner_node(quick_state)
        assert result == {}

    @pytest.mark.asyncio()
    async def test_planning_disabled_skips(self, full_state):
        """LANGGRAPH_PLANNING_ENABLED=False면 노드가 빈 dict 반환."""
        with patch("services.agent.nodes.location_planner.LANGGRAPH_PLANNING_ENABLED", False):
            result = await location_planner_node(full_state)
        assert result == {}

    @pytest.mark.asyncio()
    async def test_no_gemini_client_skips(self, full_state):
        """LLM provider 에러 시 빈 dict 반환 (graceful degradation)."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=RuntimeError("provider unavailable"))

        with (
            patch("services.agent.nodes.location_planner.LANGGRAPH_PLANNING_ENABLED", True),
            patch("services.agent.nodes.location_planner.get_llm_provider", return_value=mock_provider),
        ):
            result = await location_planner_node(full_state)
        assert result == {}

    @pytest.mark.asyncio()
    async def test_successful_location_planning(self, full_state):
        """정상 케이스: writer_plan.locations가 설정된다."""
        mock_llm_resp = MagicMock()
        mock_llm_resp.text = '{"total_scenes": 5, "locations": [{"name": "kitchen", "scenes": [0, 1, 2, 3, 4], "tags": ["kitchen", "indoors"]}]}'
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_llm_resp)

        with (
            patch("services.agent.nodes.location_planner.LANGGRAPH_PLANNING_ENABLED", True),
            patch("services.agent.nodes.location_planner.get_llm_provider", return_value=mock_provider),
        ):
            result = await location_planner_node(full_state)

        assert "writer_plan" in result
        locs = result["writer_plan"]["locations"]
        assert len(locs) == 1
        assert locs[0]["name"] == "kitchen"
        assert "indoors" in locs[0]["tags"]

    @pytest.mark.asyncio()
    async def test_preserves_existing_writer_plan(self, full_state):
        """기존 writer_plan 필드를 보존하면서 locations를 추가한다."""
        full_state["writer_plan"] = {"hook_strategy": "기존 훅", "emotional_arc": ["기대", "감동"]}

        mock_llm_resp = MagicMock()
        mock_llm_resp.text = '{"total_scenes": 2, "locations": [{"name": "room", "scenes": [0, 1], "tags": ["indoors"]}]}'
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_llm_resp)

        with (
            patch("services.agent.nodes.location_planner.LANGGRAPH_PLANNING_ENABLED", True),
            patch("services.agent.nodes.location_planner.get_llm_provider", return_value=mock_provider),
        ):
            result = await location_planner_node(full_state)

        wp = result["writer_plan"]
        assert wp["hook_strategy"] == "기존 훅"
        assert wp["locations"][0]["name"] == "room"

    @pytest.mark.asyncio()
    async def test_gemini_failure_returns_empty(self, full_state):
        """LLM 호출 실패 시 빈 dict 반환 (graceful degradation)."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=Exception("API error"))

        with (
            patch("services.agent.nodes.location_planner.LANGGRAPH_PLANNING_ENABLED", True),
            patch("services.agent.nodes.location_planner.get_llm_provider", return_value=mock_provider),
        ):
            result = await location_planner_node(full_state)

        assert result == {}

    @pytest.mark.asyncio()
    async def test_empty_locations_returns_empty(self, full_state):
        """빈 locations 응답 시 빈 dict 반환."""
        mock_llm_resp = MagicMock()
        mock_llm_resp.text = '{"total_scenes": 5, "locations": []}'
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=mock_llm_resp)

        with (
            patch("services.agent.nodes.location_planner.LANGGRAPH_PLANNING_ENABLED", True),
            patch("services.agent.nodes.location_planner.get_llm_provider", return_value=mock_provider),
        ):
            result = await location_planner_node(full_state)

        assert result == {}
