"""Revise 노드 — rollback 경로 테스트.

P0: score 하락 시 best_draft_scenes로 rollback + revision_count 강제 종료.
"""

from __future__ import annotations

import pytest

from config import LANGGRAPH_MAX_REVISIONS
from services.agent.nodes.revise import revise_node


def _make_scene(speaker: str = "A", script: str = "test") -> dict:
    return {
        "scene_id": 1,
        "script": script,
        "speaker": speaker,
        "duration": 3,
        "image_prompt": "1girl, solo",
    }


def _state(**overrides) -> dict:
    return {
        "revision_count": 0,
        "revision_history": [],
        "review_result": {"errors": [], "warnings": [], "passed": False},
        "review_reflection": None,
        "director_checkpoint_score": None,
        "draft_scenes": [_make_scene()],
        "best_draft_scenes": None,
        "best_narrative_score": 0.0,
        "topic": "test",
        "description": "",
        "duration": 10,
        "style": "Anime",
        "language": "korean",
        "structure": "monologue",
        "actor_a_gender": "female",
        "character_id": None,
        "character_b_id": None,
        "group_id": None,
        "human_feedback": None,
        "revision_feedback": None,
        "director_feedback": None,
        "critic_result": None,
        **overrides,
    }


class TestReviseRollback:
    """Revise rollback: score 하락 시 best scenes 복원."""

    @pytest.mark.asyncio
    async def test_rollback_on_score_drop(self):
        """score가 best 대비 0.1 이상 하락하면 rollback 발생."""
        best = [_make_scene(script="best scene")]
        state = _state(
            revision_count=1,
            review_result={
                "errors": ["some error"],
                "warnings": [],
                "passed": False,
                "narrative_score": {"overall": 0.4},
            },
            best_draft_scenes=best,
            best_narrative_score=0.9,
            draft_scenes=[_make_scene(script="worse scene")],
        )
        result = await revise_node(state)

        assert result["draft_scenes"][0]["script"] == "best scene"
        assert result["revision_count"] == LANGGRAPH_MAX_REVISIONS
        assert result["revision_history"][-1]["tier"] == "rollback"

    @pytest.mark.asyncio
    async def test_no_rollback_on_small_drop(self):
        """score 하락이 0.1 미만이면 rollback하지 않고 정상 revise."""
        best = [_make_scene(script="best scene")]
        state = _state(
            revision_count=1,
            review_result={
                "errors": ["씬 1: duration이 0 이하 (0)"],
                "warnings": [],
                "passed": False,
                "narrative_score": {"overall": 0.85},
            },
            best_draft_scenes=best,
            best_narrative_score=0.9,
            draft_scenes=[_make_scene(script="slightly worse")],
        )
        result = await revise_node(state)

        # 0.9 - 0.85 = 0.05 < 0.1 → rollback 안 함, 정상 revise
        assert result["revision_count"] == 2  # count + 1
        assert result["revision_history"][-1]["tier"] != "rollback"

    @pytest.mark.asyncio
    async def test_no_rollback_on_first_revision(self):
        """첫 번째 revise(count=0)에서는 rollback하지 않음."""
        best = [_make_scene(script="best scene")]
        state = _state(
            revision_count=0,
            review_result={
                "errors": ["씬 1: duration이 0 이하 (0)"],
                "warnings": [],
                "passed": False,
                "narrative_score": {"overall": 0.3},
            },
            best_draft_scenes=best,
            best_narrative_score=0.9,
            draft_scenes=[_make_scene(script="bad scene")],
        )
        result = await revise_node(state)

        # count=0이면 rollback 스킵
        assert result["revision_count"] == 1
        assert result["revision_history"][-1]["tier"] != "rollback"

    @pytest.mark.asyncio
    async def test_no_rollback_without_best_scenes(self):
        """best_draft_scenes가 없으면 rollback 불가."""
        state = _state(
            revision_count=1,
            review_result={
                "errors": ["씬 1: duration이 0 이하 (0)"],
                "warnings": [],
                "passed": False,
                "narrative_score": {"overall": 0.3},
            },
            best_draft_scenes=None,
            best_narrative_score=0.0,
            draft_scenes=[_make_scene()],
        )
        result = await revise_node(state)

        assert result["revision_count"] == 2
        assert result["revision_history"][-1]["tier"] != "rollback"

    @pytest.mark.asyncio
    async def test_rollback_uses_deepcopy(self):
        """rollback 시 deepcopy로 복원하여 원본 best_scenes 오염 방지."""
        inner = {"tags": ["a", "b"]}
        best = [{"scene_id": 1, "script": "best", "speaker": "A", "duration": 3, "image_prompt": "x", "nested": inner}]
        state = _state(
            revision_count=1,
            review_result={
                "errors": ["some error"],
                "warnings": [],
                "passed": False,
                "narrative_score": {"overall": 0.3},
            },
            best_draft_scenes=best,
            best_narrative_score=0.9,
            draft_scenes=[_make_scene()],
        )
        result = await revise_node(state)

        restored = result["draft_scenes"][0]
        # 수정해도 원본에 영향 없어야 함
        restored["nested"]["tags"].append("c")
        assert inner["tags"] == ["a", "b"]  # 원본 불변
