"""Tests for Creative Leader — evaluation, synthesis, and feedback builder."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from models.creative import CreativeSession


@pytest.fixture
def sample_session(db_session):
    session = CreativeSession(
        task_type="scenario",
        objective="Write a dramatic short",
        evaluation_criteria={
            "originality": {"weight": 0.3, "description": "Novel ideas"},
            "coherence": {"weight": 0.4, "description": "Logical flow"},
        },
        agent_config=[
            {"preset_id": 1, "role": "writer_bold"},
            {"preset_id": 2, "role": "writer_stable"},
        ],
        max_rounds=3,
        status="running",
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def sample_gen_results():
    return [
        {
            "agent_role": "writer_bold",
            "output": "Bold dramatic scene",
            "content": "Bold dramatic scene",
            "model_id": "gemini-2.0-flash",
        },
        {
            "agent_role": "writer_stable",
            "output": "Stable structured scene",
            "content": "Stable structured scene",
            "model_id": "gemini-2.0-flash",
        },
    ]


@pytest.fixture
def sample_evaluation():
    return {
        "summary": "Bold agent showed stronger creativity",
        "decision": "converged",
        "scores": {
            "writer_bold": {"score": 0.85, "feedback": "Creative but needs structure"},
            "writer_stable": {"score": 0.75, "feedback": "Well-structured but predictable"},
        },
        "best_agent_role": "writer_bold",
        "best_score": 0.85,
        "direction": "Focus on combining creativity with structure",
    }


class TestEvaluateRound:
    @pytest.mark.asyncio
    async def test_returns_direction(self, sample_session, sample_gen_results):
        from services.creative_leader import evaluate_round

        mock_response = {
            "content": '{"summary": "Good round", "decision": "continue", '
            '"scores": {"writer_bold": {"score": 0.8, "feedback": "Great"}, '
            '"writer_stable": {"score": 0.7, "feedback": "OK"}}, '
            '"best_agent_role": "writer_bold", "best_score": 0.8, '
            '"direction": "Improve emotional depth"}'
        }

        with patch(
            "services.creative_leader.get_provider",
            return_value=AsyncMock(generate=AsyncMock(return_value=mock_response)),
        ):
            result = await evaluate_round(
                session=sample_session,
                round_number=1,
                gen_results=sample_gen_results,
            )

        assert "direction" in result
        assert result["direction"] == "Improve emotional depth"
        assert result["decision"] == "continue"
        assert "writer_bold" in result["scores"]

    @pytest.mark.asyncio
    async def test_with_prev_evaluation(self, sample_session, sample_gen_results, sample_evaluation):
        from services.creative_leader import evaluate_round

        mock_response = {
            "content": '{"summary": "Improved", "decision": "converged", '
            '"scores": {"writer_bold": {"score": 0.9, "feedback": "Excellent"}, '
            '"writer_stable": {"score": 0.85, "feedback": "Good"}}, '
            '"best_agent_role": "writer_bold", "best_score": 0.9, '
            '"direction": "Final polish"}'
        }

        with patch(
            "services.creative_leader.get_provider",
            return_value=AsyncMock(generate=AsyncMock(return_value=mock_response)),
        ) as mock_get:
            result = await evaluate_round(
                session=sample_session,
                round_number=2,
                gen_results=sample_gen_results,
                prev_evaluation=sample_evaluation,
            )
            # Verify prev_evaluation was included in the prompt
            call_args = mock_get.return_value.generate.call_args
            assert "이전 라운드 평가" in call_args.kwargs["prompt"]

        assert result["decision"] == "converged"
        assert result["best_score"] == 0.9

    @pytest.mark.asyncio
    async def test_fallback_includes_direction(self, sample_session, sample_gen_results):
        from services.creative_leader import evaluate_round

        with patch(
            "services.creative_leader.get_provider",
            return_value=AsyncMock(generate=AsyncMock(return_value={"content": "not json"})),
        ):
            result = await evaluate_round(
                session=sample_session,
                round_number=1,
                gen_results=sample_gen_results,
            )

        assert "direction" in result
        assert result["direction"] == ""
        assert result["decision"] == "continue"


class TestSynthesizeOutput:
    @pytest.mark.asyncio
    async def test_returns_synthesis(self, sample_session, sample_gen_results, sample_evaluation):
        from services.creative_leader import synthesize_output

        mock_response = {"content": "Synthesized masterpiece combining both strengths"}

        with patch(
            "services.creative_leader.get_provider",
            return_value=AsyncMock(generate=AsyncMock(return_value=mock_response)),
        ):
            result = await synthesize_output(
                session=sample_session,
                gen_results=sample_gen_results,
                evaluation=sample_evaluation,
            )

        assert result["agent_role"] == "leader_synthesis"
        assert result["content"] == "Synthesized masterpiece combining both strengths"
        assert result["score"] == 0.85

    @pytest.mark.asyncio
    async def test_fallback_on_error(self, sample_session, sample_gen_results, sample_evaluation):
        from services.creative_leader import synthesize_output

        with patch(
            "services.creative_leader.get_provider",
            return_value=AsyncMock(generate=AsyncMock(side_effect=RuntimeError("API error"))),
        ):
            result = await synthesize_output(
                session=sample_session,
                gen_results=sample_gen_results,
                evaluation=sample_evaluation,
            )

        assert result == {}


class TestBuildAgentFeedbackContext:
    def test_builds_feedback_for_each_agent(self, sample_evaluation):
        from services.creative_leader import build_agent_feedback_context

        result = build_agent_feedback_context(sample_evaluation)

        assert "writer_bold" in result
        assert "writer_stable" in result
        assert "0.85" in result["writer_bold"]
        assert "Creative but needs structure" in result["writer_bold"]
        assert "Focus on combining" in result["writer_bold"]

    def test_handles_empty_scores(self):
        from services.creative_leader import build_agent_feedback_context

        result = build_agent_feedback_context({"scores": {}, "direction": ""})
        assert result == {}

    def test_handles_missing_direction(self):
        from services.creative_leader import build_agent_feedback_context

        result = build_agent_feedback_context(
            {
                "scores": {"writer_bold": {"score": 0.8, "feedback": "Good"}},
            }
        )

        assert "writer_bold" in result
        assert "0.8" in result["writer_bold"]
