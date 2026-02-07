"""TDD tests for Creative Engine orchestration (services/creative_engine.py)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from models.creative import (
    CreativeSession,
    CreativeSessionRound,
    CreativeTrace,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_agent_config():
    return [
        {"preset_id": 1, "role": "writer_bold"},
        {"preset_id": 2, "role": "writer_stable"},
        {"preset_id": 3, "role": "writer_emotional"},
    ]


@pytest.fixture
def sample_evaluation_criteria():
    return {
        "originality": {"weight": 0.3, "description": "Novel ideas"},
        "coherence": {"weight": 0.4, "description": "Logical flow"},
        "engagement": {"weight": 0.3, "description": "Audience appeal"},
    }


@pytest.fixture
def created_session(db_session, sample_agent_config, sample_evaluation_criteria):
    """Insert a CreativeSession directly into DB for tests that need one."""
    session = CreativeSession(
        task_type="scenario",
        objective="Write a dramatic short",
        evaluation_criteria=sample_evaluation_criteria,
        agent_config=sample_agent_config,
        max_rounds=3,
        status="running",
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


def _make_generation_result(role: str, text: str, score: float = 0.0):
    """Helper to build a mock agent generation result dict."""
    return {
        "agent_role": role,
        "output": text,
        "model_id": "gemini-2.0-flash",
        "token_usage": {"prompt_tokens": 100, "completion_tokens": 50},
        "latency_ms": 200,
        "temperature": 0.9,
    }


def _make_leader_evaluation(agents: list[str], direction: str = "Improve next round"):
    """Helper to build a mock leader evaluation dict."""
    scores = {a: {"score": 0.7 + i * 0.05, "feedback": f"Good {a}"} for i, a in enumerate(agents)}
    best = max(scores, key=lambda k: scores[k]["score"])
    return {
        "summary": "Round evaluation summary",
        "decision": "continue",
        "scores": scores,
        "best_agent_role": best,
        "best_score": scores[best]["score"],
        "direction": direction,
    }


def _engine_patches(gen_results, leader_eval):
    """Context manager for patching generate_parallel and evaluate_round."""
    return (
        patch(
            "services.creative_engine.generate_parallel",
            new_callable=AsyncMock,
            return_value=gen_results,
        ),
        patch(
            "services.creative_engine.evaluate_round",
            new_callable=AsyncMock,
            return_value=leader_eval,
        ),
    )


# ===========================================================================
# 1. create_session
# ===========================================================================


class TestCreateSession:
    @pytest.mark.asyncio
    async def test_creates_session_with_running_status(
        self, db_session, sample_agent_config, sample_evaluation_criteria
    ):
        from services.creative_engine import create_session

        session = await create_session(
            db=db_session,
            task_type="scenario",
            objective="Write a comedic short",
            evaluation_criteria=sample_evaluation_criteria,
            agent_config=sample_agent_config,
            max_rounds=3,
        )

        assert isinstance(session, CreativeSession)
        assert session.status == "running"
        assert session.task_type == "scenario"
        assert session.objective == "Write a comedic short"
        assert session.max_rounds == 3
        assert session.final_output is None

    @pytest.mark.asyncio
    async def test_default_evaluation_criteria_for_scenario(self, db_session, sample_agent_config):
        """When evaluation_criteria is None and task_type='scenario', defaults are applied."""
        from services.creative_engine import create_session

        session = await create_session(
            db=db_session,
            task_type="scenario",
            objective="Test objective",
            evaluation_criteria=None,
            agent_config=sample_agent_config,
        )

        assert session.evaluation_criteria is not None
        assert isinstance(session.evaluation_criteria, dict)
        assert len(session.evaluation_criteria) > 0

    @pytest.mark.asyncio
    async def test_auto_assigns_system_presets_when_agent_config_none(self, db_session):
        """When agent_config is None, system presets (excluding Leader) are auto-assigned."""
        from models.creative import CreativeAgentPreset
        from services.creative_engine import create_session

        # Insert system presets into DB
        presets = [
            CreativeAgentPreset(
                name="Leader",
                role_description="Evaluator",
                system_prompt="Evaluate",
                model_provider="gemini",
                model_name="gemini-2.0-flash",
                is_system=True,
            ),
            CreativeAgentPreset(
                name="파격형",
                role_description="Bold writer",
                system_prompt="Be bold",
                model_provider="gemini",
                model_name="gemini-2.0-flash",
                is_system=True,
            ),
            CreativeAgentPreset(
                name="안정형",
                role_description="Stable writer",
                system_prompt="Be stable",
                model_provider="gemini",
                model_name="gemini-2.0-flash",
                is_system=True,
            ),
        ]
        for p in presets:
            db_session.add(p)
        db_session.commit()

        session = await create_session(
            db=db_session,
            task_type="scenario",
            objective="Auto-preset test",
            agent_config=None,
        )

        assert session.agent_config is not None
        assert len(session.agent_config) == 2  # Leader excluded
        roles = {cfg["role"] for cfg in session.agent_config}
        assert "Leader" not in roles
        assert "파격형" in roles
        assert "안정형" in roles
        # Each config must have a preset_id
        for cfg in session.agent_config:
            assert "preset_id" in cfg
            assert cfg["preset_id"] is not None

    @pytest.mark.asyncio
    async def test_stores_agent_config_as_jsonb(self, db_session, sample_agent_config):
        from services.creative_engine import create_session

        session = await create_session(
            db=db_session,
            task_type="scenario",
            objective="Config test",
            agent_config=sample_agent_config,
        )

        # Reload from DB to verify JSONB persistence
        db_session.refresh(session)
        assert session.agent_config == sample_agent_config
        assert session.agent_config[0]["role"] == "writer_bold"


# ===========================================================================
# 2. run_round
# ===========================================================================


class TestRunRound:
    @pytest.mark.asyncio
    async def test_creates_round_with_traces(self, db_session, created_session):
        from services.creative_engine import run_round

        agents = ["writer_bold", "writer_stable", "writer_emotional"]
        gen_results = [_make_generation_result(r, f"Output from {r}") for r in agents]
        leader_eval = _make_leader_evaluation(agents)

        p_gen, p_eval = _engine_patches(gen_results, leader_eval)
        with p_gen, p_eval:
            rnd = await run_round(
                db=db_session,
                session_id=created_session.id,
                round_number=1,
            )

        assert isinstance(rnd, CreativeSessionRound)
        assert rnd.round_number == 1
        assert rnd.leader_summary == "Round evaluation summary"
        assert rnd.round_decision == "continue"

    @pytest.mark.asyncio
    async def test_trace_type_sequence(self, db_session, created_session):
        """Traces must follow: instruction -> generation (x N agents) -> evaluation."""
        from services.creative_engine import run_round

        agents = ["writer_bold", "writer_stable"]
        gen_results = [_make_generation_result(r, f"Text {r}") for r in agents]
        leader_eval = _make_leader_evaluation(agents)

        p_gen, p_eval = _engine_patches(gen_results, leader_eval)
        with p_gen, p_eval:
            await run_round(db=db_session, session_id=created_session.id, round_number=1)

        traces = (
            db_session.query(CreativeTrace)
            .filter(CreativeTrace.session_id == created_session.id)
            .order_by(CreativeTrace.sequence)
            .all()
        )

        trace_types = [t.trace_type for t in traces]
        assert trace_types[0] == "instruction"
        for tt in trace_types[1:-1]:
            assert tt == "generation"
        assert trace_types[-1] == "evaluation"

    @pytest.mark.asyncio
    async def test_leader_evaluation_includes_per_agent_scores(self, db_session, created_session):
        from services.creative_engine import run_round

        agents = ["writer_bold", "writer_stable"]
        gen_results = [_make_generation_result(r, f"Text {r}") for r in agents]
        leader_eval = _make_leader_evaluation(agents)

        p_gen, p_eval = _engine_patches(gen_results, leader_eval)
        with p_gen, p_eval:
            rnd = await run_round(db=db_session, session_id=created_session.id, round_number=1)

        assert rnd.best_agent_role is not None
        assert rnd.best_score is not None
        assert rnd.best_score > 0

    @pytest.mark.asyncio
    async def test_stores_leader_direction(self, db_session, created_session):
        """Round should store leader_direction from evaluation."""
        from services.creative_engine import run_round

        agents = ["writer_bold", "writer_stable"]
        gen_results = [_make_generation_result(r, f"Text {r}") for r in agents]
        leader_eval = _make_leader_evaluation(agents, direction="Focus on emotional depth")

        p_gen, p_eval = _engine_patches(gen_results, leader_eval)
        with p_gen, p_eval:
            rnd = await run_round(db=db_session, session_id=created_session.id, round_number=1)

        assert rnd.leader_direction == "Focus on emotional depth"

    @pytest.mark.asyncio
    async def test_writes_agent_scores_to_traces(self, db_session, created_session):
        """Generation traces should have score/feedback after evaluation."""
        from services.creative_engine import run_round

        agents = ["writer_bold", "writer_stable"]
        gen_results = [_make_generation_result(r, f"Text {r}") for r in agents]
        leader_eval = _make_leader_evaluation(agents)

        p_gen, p_eval = _engine_patches(gen_results, leader_eval)
        with p_gen, p_eval:
            await run_round(db=db_session, session_id=created_session.id, round_number=1)

        gen_traces = (
            db_session.query(CreativeTrace)
            .filter(
                CreativeTrace.session_id == created_session.id,
                CreativeTrace.trace_type == "generation",
            )
            .all()
        )
        for trace in gen_traces:
            assert trace.score is not None
            assert trace.feedback is not None

    @pytest.mark.asyncio
    async def test_evaluation_trace_stores_full_json(self, db_session, created_session):
        """Evaluation trace should contain full JSON (not just summary)."""
        from services.creative_engine import run_round

        agents = ["writer_bold"]
        gen_results = [_make_generation_result("writer_bold", "Text")]
        leader_eval = _make_leader_evaluation(agents)

        p_gen, p_eval = _engine_patches(gen_results, leader_eval)
        with p_gen, p_eval:
            await run_round(db=db_session, session_id=created_session.id, round_number=1)

        eval_trace = (
            db_session.query(CreativeTrace)
            .filter(
                CreativeTrace.session_id == created_session.id,
                CreativeTrace.trace_type == "evaluation",
            )
            .first()
        )
        parsed = json.loads(eval_trace.output_content)
        assert "scores" in parsed
        assert "direction" in parsed

    @pytest.mark.asyncio
    async def test_run_round_injects_feedback(self, db_session, created_session):
        """Round 2+ should inject per-agent feedback into agent objectives."""
        from services.creative_engine import run_round
        from services.creative_trace import record_trace

        # Simulate round 1 evaluation trace
        r1_eval = _make_leader_evaluation(
            ["writer_bold", "writer_stable", "writer_emotional"],
            direction="Be more creative",
        )
        await record_trace(
            db=db_session,
            session_id=created_session.id,
            round_number=1,
            sequence=0,
            trace_type="evaluation",
            agent_role="leader",
            input_prompt="eval",
            output_content=json.dumps(r1_eval, ensure_ascii=False),
            model_id="gemini-2.0-flash",
            token_usage={},
            latency_ms=0,
            temperature=0.3,
        )
        db_session.commit()

        agents = ["writer_bold", "writer_stable", "writer_emotional"]
        gen_results = [_make_generation_result(r, f"Text {r}") for r in agents]
        leader_eval = _make_leader_evaluation(agents)

        with (
            patch(
                "services.creative_engine.generate_parallel",
                new_callable=AsyncMock,
                return_value=gen_results,
            ) as mock_gen,
            patch(
                "services.creative_engine.evaluate_round",
                new_callable=AsyncMock,
                return_value=leader_eval,
            ),
        ):
            await run_round(db=db_session, session_id=created_session.id, round_number=2)

            # Check that agents received feedback via objective
            called_agents = mock_gen.call_args.kwargs.get("agents", mock_gen.call_args[1].get("agents", []))
            for agent in called_agents:
                if agent["role"] in r1_eval["scores"]:
                    assert "objective" in agent
                    assert "이전 라운드 피드백" in agent["objective"]


# ===========================================================================
# 3. run_debate
# ===========================================================================


class TestRunDebate:
    @pytest.mark.asyncio
    async def test_runs_up_to_max_rounds(self, db_session, created_session):
        from services.creative_engine import run_debate

        leader_eval = _make_leader_evaluation(["writer_bold", "writer_stable"])
        leader_eval["decision"] = "continue"  # never converge

        gen_results = [
            _make_generation_result("writer_bold", "Bold text"),
            _make_generation_result("writer_stable", "Stable text"),
        ]

        p_gen, p_eval = _engine_patches(gen_results, leader_eval)
        with p_gen, p_eval:
            await run_debate(db=db_session, session_id=created_session.id)

        rounds = (
            db_session.query(CreativeSessionRound).filter(CreativeSessionRound.session_id == created_session.id).all()
        )
        assert len(rounds) == created_session.max_rounds

    @pytest.mark.asyncio
    async def test_stops_early_on_converged(self, db_session, created_session):
        from services.creative_engine import run_debate

        converged_eval = _make_leader_evaluation(["writer_bold", "writer_stable"])
        converged_eval["decision"] = "converged"

        gen_results = [
            _make_generation_result("writer_bold", "Bold text"),
            _make_generation_result("writer_stable", "Stable text"),
        ]

        p_gen, p_eval = _engine_patches(gen_results, converged_eval)
        with p_gen, p_eval:
            result = await run_debate(db=db_session, session_id=created_session.id)

        rounds = (
            db_session.query(CreativeSessionRound).filter(CreativeSessionRound.session_id == created_session.id).all()
        )
        assert len(rounds) == 1  # stopped after first round
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_updates_status_to_completed(self, db_session, created_session):
        from services.creative_engine import run_debate

        converged_eval = _make_leader_evaluation(["writer_bold"])
        converged_eval["decision"] = "converged"

        gen_results = [_make_generation_result("writer_bold", "Final")]

        p_gen, p_eval = _engine_patches(gen_results, converged_eval)
        with p_gen, p_eval:
            result = await run_debate(db=db_session, session_id=created_session.id)

        db_session.refresh(result)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_calculates_total_token_usage(self, db_session, created_session):
        from services.creative_engine import run_debate

        converged_eval = _make_leader_evaluation(["writer_bold"])
        converged_eval["decision"] = "converged"

        gen_results = [_make_generation_result("writer_bold", "Output")]

        p_gen, p_eval = _engine_patches(gen_results, converged_eval)
        with p_gen, p_eval:
            result = await run_debate(db=db_session, session_id=created_session.id)

        assert result.total_token_usage is not None
        assert "prompt_tokens" in result.total_token_usage
        assert "completion_tokens" in result.total_token_usage

    @pytest.mark.asyncio
    async def test_auto_finalizes_with_best_output(self, db_session, created_session):
        from services.creative_engine import run_debate

        converged_eval = _make_leader_evaluation(["writer_bold", "writer_stable"])
        converged_eval["decision"] = "converged"

        gen_results = [
            _make_generation_result("writer_bold", "Bold final output"),
            _make_generation_result("writer_stable", "Stable final output"),
        ]

        p_gen, p_eval = _engine_patches(gen_results, converged_eval)
        with (
            p_gen,
            p_eval,
            patch(
                "services.creative_engine.synthesize_output",
                new_callable=AsyncMock,
                return_value={
                    "content": "Synthesized output",
                    "agent_role": "leader_synthesis",
                    "score": 0.85,
                },
            ),
        ):
            result = await run_debate(db=db_session, session_id=created_session.id)

        assert result.final_output is not None
        assert result.context.get("auto_finalized") is True

    @pytest.mark.asyncio
    async def test_synthesizes_on_converge(self, db_session, created_session):
        """When converged, run_debate should call synthesize_output."""
        from services.creative_engine import run_debate

        converged_eval = _make_leader_evaluation(["writer_bold", "writer_stable"])
        converged_eval["decision"] = "converged"

        gen_results = [
            _make_generation_result("writer_bold", "Bold output"),
            _make_generation_result("writer_stable", "Stable output"),
        ]

        synthesis_result = {
            "content": "Best of both worlds",
            "agent_role": "leader_synthesis",
            "score": 0.9,
        }

        p_gen, p_eval = _engine_patches(gen_results, converged_eval)
        with (
            p_gen,
            p_eval,
            patch(
                "services.creative_engine.synthesize_output",
                new_callable=AsyncMock,
                return_value=synthesis_result,
            ) as mock_synth,
        ):
            result = await run_debate(db=db_session, session_id=created_session.id)

        mock_synth.assert_called_once()
        assert result.final_output["agent_role"] == "leader_synthesis"
        assert result.final_output["content"] == "Best of both worlds"

    @pytest.mark.asyncio
    async def test_falls_back_to_best_when_synthesis_fails(self, db_session, created_session):
        """If synthesize returns empty, fall back to best agent output."""
        from services.creative_engine import run_debate

        converged_eval = _make_leader_evaluation(["writer_bold", "writer_stable"])
        converged_eval["decision"] = "converged"

        gen_results = [
            _make_generation_result("writer_bold", "Bold output"),
            _make_generation_result("writer_stable", "Stable output"),
        ]

        p_gen, p_eval = _engine_patches(gen_results, converged_eval)
        with (
            p_gen,
            p_eval,
            patch(
                "services.creative_engine.synthesize_output",
                new_callable=AsyncMock,
                return_value={},  # synthesis failed
            ),
        ):
            result = await run_debate(db=db_session, session_id=created_session.id)

        assert result.final_output is not None
        assert result.final_output["agent_role"] == converged_eval["best_agent_role"]


# ===========================================================================
# 4. finalize
# ===========================================================================


class TestFinalize:
    @pytest.mark.asyncio
    async def test_sets_final_output_and_completed(self, db_session, created_session):
        from services.creative_engine import finalize

        selected = {"title": "Best Scene", "content": "Dramatic ending"}
        result = await finalize(
            db=db_session,
            session_id=created_session.id,
            selected_output=selected,
            reason="Best overall quality",
        )

        assert result.final_output == selected
        assert result.status == "completed"

        db_session.refresh(result)
        assert result.final_output["title"] == "Best Scene"

    @pytest.mark.asyncio
    async def test_allows_re_finalize(self, db_session, created_session):
        from services.creative_engine import finalize

        created_session.status = "completed"
        created_session.final_output = {"already": "done"}
        created_session.context = {"auto_finalized": True}
        db_session.commit()

        new_output = {"content": "New selected output", "agent_role": "writer_bold"}
        result = await finalize(
            db=db_session,
            session_id=created_session.id,
            selected_output=new_output,
            reason="Manual selection",
        )

        assert result.final_output == new_output
        assert result.context.get("auto_finalized") is False
        assert result.context.get("finalize_reason") == "Manual selection"


# ===========================================================================
# 5. record_trace (services/creative_trace.py)
# ===========================================================================


class TestRecordTrace:
    @pytest.mark.asyncio
    async def test_creates_trace_with_all_fields(self, db_session, created_session):
        from services.creative_trace import record_trace

        trace = await record_trace(
            db=db_session,
            session_id=created_session.id,
            round_number=1,
            sequence=1,
            trace_type="generation",
            agent_role="writer_bold",
            input_prompt="Write a scene about...",
            output_content="It was a dark and stormy night.",
            model_id="gemini-2.0-flash",
            token_usage={"prompt_tokens": 120, "completion_tokens": 80},
            latency_ms=350,
            temperature=0.9,
            score=0.85,
            feedback="Creative opening",
        )

        assert isinstance(trace, CreativeTrace)
        assert trace.session_id == created_session.id
        assert trace.round_number == 1
        assert trace.sequence == 1
        assert trace.trace_type == "generation"
        assert trace.agent_role == "writer_bold"
        assert trace.input_prompt == "Write a scene about..."
        assert trace.output_content == "It was a dark and stormy night."
        assert trace.model_id == "gemini-2.0-flash"
        assert trace.token_usage["prompt_tokens"] == 120
        assert trace.latency_ms == 350
        assert trace.temperature == 0.9
        assert trace.score == 0.85
        assert trace.feedback == "Creative opening"


# ===========================================================================
# 6. get_session_timeline (services/creative_trace.py)
# ===========================================================================


class TestGetSessionTimeline:
    @pytest.mark.asyncio
    async def test_returns_ordered_timeline(self, db_session, created_session):
        from services.creative_trace import get_session_timeline, record_trace

        # Create traces in deliberate non-sequential insert order
        await record_trace(
            db=db_session,
            session_id=created_session.id,
            round_number=1,
            sequence=2,
            trace_type="generation",
            agent_role="writer_stable",
            input_prompt="p",
            output_content="o",
            model_id="gemini-2.0-flash",
            token_usage={},
            latency_ms=100,
            temperature=0.9,
        )
        await record_trace(
            db=db_session,
            session_id=created_session.id,
            round_number=1,
            sequence=1,
            trace_type="instruction",
            agent_role="leader",
            input_prompt="p",
            output_content="o",
            model_id="gemini-2.0-flash",
            token_usage={},
            latency_ms=50,
            temperature=0.7,
        )

        timeline = await get_session_timeline(db=db_session, session_id=created_session.id)

        assert "session" in timeline
        assert "rounds" in timeline
        assert "traces" in timeline
        assert timeline["session"]["id"] == created_session.id

        traces = timeline["traces"]
        assert len(traces) == 2
        # Must be sorted by (round_number, sequence)
        assert traces[0]["sequence"] < traces[1]["sequence"]
