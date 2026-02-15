"""Tests for Creative Lab Pipeline — StepDef registry, disabled_steps, Director QC integration.

Covers:
- StepDef registry structure validation
- _commit_step() state management
- disabled_steps skip behavior in run_pipeline()
- Director QC auto-approve / pause-for-review flow
- Pipeline resumability (already-completed steps)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ── Fixtures ─────────────────────────────────────────────────


def _make_session(
    session_id: int = 1,
    status: str = "phase2_running",
    context: dict | None = None,
) -> MagicMock:
    session = MagicMock()
    session.id = session_id
    session.status = status
    session.context = context or {}
    session.session_type = "shorts"
    session.final_output = None
    session.total_token_usage = None
    return session


def _base_context(disabled_steps: list[str] | None = None) -> dict:
    return {
        "selected_concept": {"title": "Test", "hook": "Hook"},
        "duration": 30,
        "structure": "Monologue",
        "language": "Korean",
        "character_name": "하루",
        "characters": {"A": {"id": 1, "name": "하루", "tags": ["1girl"]}},
        "disabled_steps": disabled_steps or [],
        "pipeline": {"state": {}, "progress": {}, "logs": []},
    }


# ── StepDef Registry ────────────────────────────────────────


class TestStepDefRegistry:
    def test_pipeline_steps_has_five_entries(self):
        from services.creative_pipeline import PIPELINE_STEPS

        assert len(PIPELINE_STEPS) == 5

    def test_step_names_match_expected_order(self):
        from services.creative_pipeline import PIPELINE_STEPS

        names = [s.name for s in PIPELINE_STEPS]
        assert names == ["scriptwriter", "cinematographer", "tts_designer", "sound_designer", "copyright_reviewer"]

    def test_each_step_has_required_fields(self):
        from services.creative_pipeline import PIPELINE_STEPS

        for step in PIPELINE_STEPS:
            assert step.name, "Step must have a name"
            assert step.template, "Step must have a template"
            assert callable(step.validate_fn), "Step must have a callable validate_fn"
            assert isinstance(step.scenes_key, str), "scenes_key must be a string"

    def test_scenes_key_varies_by_step(self):
        from services.creative_pipeline import PIPELINE_STEPS

        keys = {s.name: s.scenes_key for s in PIPELINE_STEPS}
        assert keys["scriptwriter"] == "scenes"
        assert keys["cinematographer"] == "scenes"
        assert keys["tts_designer"] == "tts_designs"
        assert keys["sound_designer"] == "recommendation"
        assert keys["copyright_reviewer"] == "checks"


# ── _commit_step ─────────────────────────────────────────────


class TestCommitStep:
    def test_commit_step_updates_progress_and_state(self):
        from services.creative_pipeline import _commit_step

        db = MagicMock()
        session = _make_session(context={"pipeline": {"state": {}, "progress": {}}})

        _commit_step(db, session, "scriptwriter", "done", {"scriptwriter_result": {"scenes": []}})

        pipeline = session.context["pipeline"]
        assert pipeline["progress"]["scriptwriter"] == "done"
        assert pipeline["current_step"] == "scriptwriter"
        assert "heartbeat" in pipeline
        db.commit.assert_called_once()

    def test_commit_step_skipped_status(self):
        from services.creative_pipeline import _commit_step

        db = MagicMock()
        session = _make_session(context={"pipeline": {"state": {}, "progress": {}}})

        _commit_step(db, session, "sound_designer", "skipped", {})

        assert session.context["pipeline"]["progress"]["sound_designer"] == "skipped"
        db.commit.assert_called_once()


# ── disabled_steps in run_pipeline ────────────────────────────


class TestDisabledStepsInPipeline:
    """Tests that disabled steps are skipped with correct status and logging."""

    @patch("services.creative_pipeline.SessionLocal")
    @patch("services.creative_pipeline.finalize_pipeline")
    @patch("services.creative_pipeline._run_step_with_retry")
    @patch("services.creative_pipeline.load_preset", return_value=None)
    @patch("services.creative_pipeline.should_review", return_value=False)
    @patch("services.creative_pipeline.pipeline_log")
    @patch("services.creative_pipeline._commit_step")
    def test_disabled_step_skipped(
        self, mock_commit, mock_log, mock_review, mock_preset, mock_retry, mock_finalize, mock_session_local
    ):
        from services.creative_pipeline import run_pipeline

        ctx = _base_context(disabled_steps=["sound_designer", "copyright_reviewer"])
        session = _make_session(context=ctx)

        db = MagicMock()
        db.query.return_value.get.return_value = session
        mock_session_local.return_value = db
        mock_retry.return_value = [{"order": 0, "script": "test"}]

        run_pipeline(1)

        # Verify skipped steps get "skipped" status
        skip_calls = [c for c in mock_commit.call_args_list if c[0][3] == "skipped"]
        assert len(skip_calls) == 2
        skipped_names = {c[0][2] for c in skip_calls}
        assert skipped_names == {"sound_designer", "copyright_reviewer"}

        # Verify non-disabled steps ran
        done_calls = [c for c in mock_commit.call_args_list if c[0][3] == "done"]
        assert len(done_calls) == 3
        done_names = {c[0][2] for c in done_calls}
        assert done_names == {"scriptwriter", "cinematographer", "tts_designer"}

    @patch("services.creative_pipeline.SessionLocal")
    @patch("services.creative_pipeline.finalize_pipeline")
    @patch("services.creative_pipeline._run_step_with_retry")
    @patch("services.creative_pipeline.load_preset", return_value=None)
    @patch("services.creative_pipeline.should_review", return_value=False)
    @patch("services.creative_pipeline.pipeline_log")
    @patch("services.creative_pipeline._commit_step")
    def test_disabled_step_logged(
        self, mock_commit, mock_log, mock_review, mock_preset, mock_retry, mock_finalize, mock_session_local
    ):
        from services.creative_pipeline import run_pipeline

        ctx = _base_context(disabled_steps=["sound_designer"])
        session = _make_session(context=ctx)

        db = MagicMock()
        db.query.return_value.get.return_value = session
        mock_session_local.return_value = db
        mock_retry.return_value = [{"order": 0}]

        run_pipeline(1)

        # Verify skip log was recorded
        skip_log_calls = [
            c for c in mock_log.call_args_list if "Skipped" in str(c[0][3]) and c[0][2] == "sound_designer"
        ]
        assert len(skip_log_calls) == 1

    @patch("services.creative_pipeline.SessionLocal")
    @patch("services.creative_pipeline.finalize_pipeline")
    @patch("services.creative_pipeline._run_step_with_retry")
    @patch("services.creative_pipeline.load_preset", return_value=None)
    @patch("services.creative_pipeline.should_review", return_value=False)
    @patch("services.creative_pipeline.pipeline_log")
    @patch("services.creative_pipeline._commit_step")
    def test_no_disabled_steps_runs_all(
        self, mock_commit, mock_log, mock_review, mock_preset, mock_retry, mock_finalize, mock_session_local
    ):
        from services.creative_pipeline import run_pipeline

        ctx = _base_context(disabled_steps=[])
        session = _make_session(context=ctx)

        db = MagicMock()
        db.query.return_value.get.return_value = session
        mock_session_local.return_value = db
        mock_retry.return_value = [{"order": 0}]

        run_pipeline(1)

        # All 5 steps should be "done" (no skipped)
        done_calls = [c for c in mock_commit.call_args_list if c[0][3] == "done"]
        assert len(done_calls) == 5

        skip_calls = [c for c in mock_commit.call_args_list if c[0][3] == "skipped"]
        assert len(skip_calls) == 0


# ── Director QC integration in pipeline ──────────────────────


class TestDirectorQCInPipeline:
    """Tests Director QC auto-approve and pause-for-review flow in run_pipeline."""

    @patch("services.creative_pipeline.SessionLocal")
    @patch("services.creative_pipeline.finalize_pipeline")
    @patch("services.creative_pipeline._run_step_with_retry")
    @patch("services.creative_pipeline.load_preset", return_value=None)
    @patch("services.creative_pipeline.should_review", return_value=True)
    @patch("services.creative_pipeline.run_step_qc")
    @patch("services.creative_pipeline.check_auto_approve", return_value=True)
    @patch("services.creative_pipeline.pipeline_log")
    @patch("services.creative_pipeline._commit_step")
    def test_auto_approve_continues_pipeline(
        self,
        mock_commit,
        mock_log,
        mock_auto,
        mock_qc,
        mock_review,
        mock_preset,
        mock_retry,
        mock_finalize,
        mock_session_local,
    ):
        from services.creative_pipeline import run_pipeline

        ctx = _base_context()
        session = _make_session(context=ctx)

        db = MagicMock()
        db.query.return_value.get.return_value = session
        mock_session_local.return_value = db
        mock_retry.return_value = [{"order": 0}]
        mock_qc.return_value = {"score": 0.9, "overall_rating": "good", "issues": []}

        run_pipeline(1)

        # All 5 steps completed + finalize called
        done_calls = [c for c in mock_commit.call_args_list if c[0][3] == "done"]
        assert len(done_calls) == 5
        mock_finalize.assert_called_once()

    @patch("services.creative_pipeline.SessionLocal")
    @patch("services.creative_pipeline.finalize_pipeline")
    @patch("services.creative_pipeline._run_step_with_retry")
    @patch("services.creative_pipeline.load_preset", return_value=None)
    @patch("services.creative_pipeline.should_review", return_value=True)
    @patch("services.creative_pipeline.run_step_qc")
    @patch("services.creative_pipeline.check_auto_approve", return_value=False)
    @patch("services.creative_pipeline.pause_for_review")
    @patch("services.creative_pipeline.pipeline_log")
    @patch("services.creative_pipeline._commit_step")
    def test_low_score_pauses_for_review(
        self,
        mock_commit,
        mock_log,
        mock_pause,
        mock_auto,
        mock_qc,
        mock_review,
        mock_preset,
        mock_retry,
        mock_finalize,
        mock_session_local,
    ):
        from services.creative_pipeline import run_pipeline

        ctx = _base_context()
        session = _make_session(context=ctx)

        db = MagicMock()
        db.query.return_value.get.return_value = session
        mock_session_local.return_value = db
        mock_retry.return_value = [{"order": 0}]
        mock_qc.return_value = {"score": 0.6, "overall_rating": "needs_revision", "issues": [{"severity": "warning"}]}

        run_pipeline(1)

        # First step done, then paused -> pipeline returns early
        mock_pause.assert_called_once()
        pause_args = mock_pause.call_args[0]
        assert pause_args[2] == "scriptwriter"  # step_name
        assert pause_args[3]["score"] == 0.6  # qc_result
        # finalize should NOT be called (pipeline paused)
        mock_finalize.assert_not_called()

    @patch("services.creative_pipeline.SessionLocal")
    @patch("services.creative_pipeline.finalize_pipeline")
    @patch("services.creative_pipeline._run_step_with_retry")
    @patch("services.creative_pipeline.load_preset", return_value=None)
    @patch("services.creative_pipeline.should_review")
    @patch("services.creative_pipeline.run_step_qc")
    @patch("services.creative_pipeline.check_auto_approve", return_value=True)
    @patch("services.creative_pipeline.pipeline_log")
    @patch("services.creative_pipeline._commit_step")
    def test_disabled_step_skips_qc(
        self,
        mock_commit,
        mock_log,
        mock_auto,
        mock_qc,
        mock_review,
        mock_preset,
        mock_retry,
        mock_finalize,
        mock_session_local,
    ):
        from services.creative_pipeline import run_pipeline

        ctx = _base_context(disabled_steps=["sound_designer"])
        session = _make_session(context=ctx)

        db = MagicMock()
        db.query.return_value.get.return_value = session
        mock_session_local.return_value = db
        mock_retry.return_value = [{"order": 0}]
        mock_qc.return_value = {"score": 0.9}
        mock_review.return_value = True

        run_pipeline(1)

        # QC should be called for 4 steps (not sound_designer)
        qc_step_names = [c[0][2] for c in mock_qc.call_args_list]
        assert "sound_designer" not in qc_step_names
        assert len(qc_step_names) == 4


# ── Resumability: already-completed steps ─────────────────────


class TestPipelineResumability:
    @patch("services.creative_pipeline.SessionLocal")
    @patch("services.creative_pipeline.finalize_pipeline")
    @patch("services.creative_pipeline._run_step_with_retry")
    @patch("services.creative_pipeline.load_preset", return_value=None)
    @patch("services.creative_pipeline.should_review", return_value=False)
    @patch("services.creative_pipeline.pipeline_log")
    @patch("services.creative_pipeline._commit_step")
    def test_skips_already_completed_steps(
        self, mock_commit, mock_log, mock_review, mock_preset, mock_retry, mock_finalize, mock_session_local
    ):
        from services.creative_pipeline import run_pipeline

        # Scriptwriter already done in state
        ctx = _base_context()
        ctx["pipeline"]["state"] = {"scriptwriter_result": {"scenes": [{"order": 0}]}}
        session = _make_session(context=ctx)

        db = MagicMock()
        db.query.return_value.get.return_value = session
        mock_session_local.return_value = db
        mock_retry.return_value = [{"order": 0}]

        run_pipeline(1)

        # Only 4 steps should run (scriptwriter skipped because already in state)
        assert mock_retry.call_count == 4
        run_step_names = [c[1]["step"].name for c in mock_retry.call_args_list]
        assert "scriptwriter" not in run_step_names
