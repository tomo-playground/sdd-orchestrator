"""Phase 12-B Group B: 12-B-3 (예외 시 자동 통과 제거), 12-B-6 (수렴 임계값 재조정) 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# 12-B-6: Convergence threshold + min rounds
# ---------------------------------------------------------------------------


class TestConvergenceMinRounds:
    """_check_convergence 최소 라운드 가드 + 임계값 재조정 테스트."""

    @pytest.mark.asyncio
    async def test_round1_high_score_returns_false(self):
        """round_num=1 + 높은 점수(0.9) -> False (최소 라운드 미달)."""
        from services.agent.nodes._debate_utils import _check_convergence

        # 높은 NarrativeScore를 유도하는 고품질 컨셉
        concept = {
            "title": "충격적인 반전의 이야기",
            "concept": "감동적인 이야기. 놀라운 반전. 슬픔과 기쁨이 교차하는 서사. 매우 강렬한 감정.",
            "strengths": ["감정 전달력", "서사 구조"],
        }
        result = await _check_convergence([concept], [], round_num=1)
        assert result is False, "최소 라운드(2) 미달 시 수렴 불가"

    @pytest.mark.asyncio
    async def test_round2_score_085_returns_true(self):
        """round_num=2 + NarrativeScore >= 0.85 -> True."""
        from services.agent.nodes._debate_utils import (
            _check_convergence,
            _estimate_narrative_score,
        )

        # 모든 요소를 갖춘 컨셉 (score = 1.0)
        concept = {
            "title": "충격적인 반전의 이야기",
            "concept": "감동적인 이야기. 놀라운 반전. 슬픔과 기쁨이 교차하는 서사. 매우 강렬한 감정.",
            "strengths": ["감정 전달력", "서사 구조"],
        }
        score = _estimate_narrative_score(concept)
        assert score >= 0.85, f"테스트 컨셉 score({score}) >= 0.85 필요"

        result = await _check_convergence([concept], [], round_num=2)
        assert result is True, "라운드 2 + 높은 점수 -> 수렴"

    @pytest.mark.asyncio
    async def test_round2_score_07_returns_false(self):
        """round_num=2 + NarrativeScore 0.7 -> False (0.85 미달, hard limit 전)."""
        from services.agent.nodes._debate_utils import (
            _check_convergence,
            _estimate_narrative_score,
        )

        # 0.7 수준의 컨셉 (hook+strengths+title = 0.3+0.2+0.2 = 0.7)
        concept = {
            "title": "평범한 이야기 제목입니다",
            "concept": "어떤 사건이 일어났다 그래서 결과가 나왔다",
            "strengths": ["흥미로운 소재", "적절한 구성"],
        }
        score = _estimate_narrative_score(concept)
        assert score < 0.85, f"테스트 컨셉 score({score}) < 0.85 필요"

        # MAX_DEBATE_ROUNDS=3으로 패치하여 hard limit에 걸리지 않도록 함
        with patch("services.agent.nodes._debate_utils.MAX_DEBATE_ROUNDS", 3):
            result = await _check_convergence([concept], [], round_num=2)
        # Hook 강도도 0.80 미만이므로 False
        assert result is False, "score < 0.85 이므로 수렴 불가"


# ---------------------------------------------------------------------------
# 12-B-3: Director Checkpoint — 재시도 + error
# ---------------------------------------------------------------------------


class TestDirectorCheckpointRetry:
    """director_checkpoint_node 예외 재시도 + error 결정 테스트."""

    @pytest.mark.asyncio
    async def test_first_fail_retry_success(self):
        """1차 실패 + 재시도 성공 -> 정상 결과 반환."""
        from services.agent.nodes.director_checkpoint import director_checkpoint_node

        state = {
            "director_plan": {"quality_criteria": []},
            "draft_scenes": [],
            "review_result": {},
            "topic": "test",
            "duration": 30,
            "director_checkpoint_revision_count": 0,
        }

        call_count = 0

        async def _mock_run_production_step(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Gemini timeout")
            return {
                "decision": "proceed",
                "score": 0.8,
                "reasoning": "good script",
                "feedback": "",
            }

        with (
            patch(
                "services.agent.nodes.director_checkpoint.run_production_step",
                side_effect=_mock_run_production_step,
            ),
            patch(
                "services.agent.nodes.director_checkpoint.trace_llm_call",
                return_value=AsyncMock(),
            ),
        ):
            result = await director_checkpoint_node(state)

        assert result["director_checkpoint_decision"] == "proceed"
        assert result["director_checkpoint_score"] == 0.8
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_both_fail_returns_error(self):
        """양쪽 실패 -> error 결정 반환."""
        from services.agent.nodes.director_checkpoint import director_checkpoint_node

        state = {
            "director_plan": {},
            "draft_scenes": [],
            "review_result": {},
            "topic": "test",
            "duration": 30,
            "director_checkpoint_revision_count": 0,
        }

        with (
            patch(
                "services.agent.nodes.director_checkpoint.run_production_step",
                side_effect=RuntimeError("persistent error"),
            ),
            patch(
                "services.agent.nodes.director_checkpoint.trace_llm_call",
                return_value=AsyncMock(),
            ),
        ):
            result = await director_checkpoint_node(state)

        assert result["director_checkpoint_decision"] == "error"
        assert "평가 불가" in result["director_checkpoint_feedback"]


# ---------------------------------------------------------------------------
# 12-B-3: Director — 재시도 + error
# ---------------------------------------------------------------------------


class TestDirectorRetry:
    """director_node 예외 재시도 + error 결정 테스트."""

    @pytest.mark.asyncio
    async def test_both_fail_returns_error(self):
        """양쪽 실패 -> error 결정 반환."""
        from services.agent.nodes.director import director_node

        state = {
            "director_revision_count": 0,
            "cinematographer_result": {},
            "tts_designer_result": {},
            "sound_designer_result": {},
            "copyright_reviewer_result": {},
            "director_plan": {},
        }

        with (
            patch(
                "services.agent.nodes.director.run_production_step",
                side_effect=RuntimeError("Gemini down"),
            ),
            patch(
                "services.agent.nodes.director.trace_llm_call",
                return_value=AsyncMock(),
            ),
        ):
            result = await director_node(state, {})

        assert result["director_decision"] == "error"
        assert "평가 불가" in result["director_feedback"]


# ---------------------------------------------------------------------------
# 12-B-3: Routing — error decision
# ---------------------------------------------------------------------------


class TestRoutingErrorDecision:
    """error decision에 대한 라우팅 테스트."""

    def test_checkpoint_error_routes_to_cinematographer(self):
        """Checkpoint error -> cinematographer (graceful proceed)."""
        from services.agent.routing import route_after_director_checkpoint

        state = {"director_checkpoint_decision": "error"}
        assert route_after_director_checkpoint(state) == "cinematographer"

    def test_director_error_routes_to_finalize(self):
        """Director error -> finalize (Phase 25: human_gate 제거)."""
        from services.agent.routing import route_after_director

        state = {"director_decision": "error", "auto_approve": False}
        assert route_after_director(state) == "finalize"

    def test_director_error_auto_approve_routes_to_finalize(self):
        """Director error + auto_approve -> finalize."""
        from services.agent.routing import route_after_director

        state = {"director_decision": "error", "auto_approve": True}
        assert route_after_director(state) == "finalize"
