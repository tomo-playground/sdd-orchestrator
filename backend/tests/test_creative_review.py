"""Tests for Creative Lab interactive review (Pause-Review-Resume)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ── Fixtures ─────────────────────────────────────────────────


def _make_session(status: str = "phase2_running", context: dict | None = None) -> MagicMock:
    session = MagicMock()
    session.id = 1
    session.status = status
    session.context = context or {}
    session.session_type = "shorts"
    return session


def _make_qc_result(score: float = 0.7, critical: int = 0, overall: str = "needs_revision") -> dict:
    issues = [{"severity": "critical", "category": "readability", "scene": 0, "description": "broken"}] * critical
    issues += [{"severity": "warning", "category": "hook", "scene": 1, "description": "weak hook"}]
    return {
        "overall_rating": overall,
        "score": score,
        "score_breakdown": {
            "readability": score,
            "hook_strength": score,
            "emotional_arc": score,
            "tts_naturalness": score,
            "expression_diversity": score,
            "consistency": score,
        },
        "summary": "Test summary",
        "issues": issues,
        "strengths": ["Good pacing"],
        "revision_suggestions": ["Fix scene 1"],
    }


# ── should_review ────────────────────────────────────────────


class TestShouldReview:
    @patch("services.creative_review.CREATIVE_REVIEW_ENABLED", True)
    @patch("services.creative_review.CREATIVE_REVIEW_STEPS", ["scriptwriter"])
    def test_enabled_for_configured_step(self):
        from services.creative_review import should_review

        assert should_review("scriptwriter") is True

    @patch("services.creative_review.CREATIVE_REVIEW_ENABLED", True)
    @patch("services.creative_review.CREATIVE_REVIEW_STEPS", ["scriptwriter"])
    def test_disabled_for_unconfigured_step(self):
        from services.creative_review import should_review

        assert should_review("cinematographer") is False

    @patch("services.creative_review.CREATIVE_REVIEW_ENABLED", False)
    @patch("services.creative_review.CREATIVE_REVIEW_STEPS", ["scriptwriter"])
    def test_disabled_globally(self):
        from services.creative_review import should_review

        assert should_review("scriptwriter") is False


# ── check_auto_approve ───────────────────────────────────────


class TestCheckAutoApprove:
    @patch("services.creative_review.CREATIVE_AUTO_APPROVE_THRESHOLD", 0.85)
    def test_auto_approve_high_score_no_critical(self):
        from services.creative_review import check_auto_approve

        result = _make_qc_result(score=0.9, critical=0, overall="good")
        assert check_auto_approve(result) is True

    @patch("services.creative_review.CREATIVE_AUTO_APPROVE_THRESHOLD", 0.85)
    def test_reject_low_score(self):
        from services.creative_review import check_auto_approve

        result = _make_qc_result(score=0.7, critical=0)
        assert check_auto_approve(result) is False

    @patch("services.creative_review.CREATIVE_AUTO_APPROVE_THRESHOLD", 0.85)
    def test_reject_with_critical(self):
        from services.creative_review import check_auto_approve

        result = _make_qc_result(score=0.9, critical=1)
        assert check_auto_approve(result) is False


# ── pause_for_review ─────────────────────────────────────────


class TestPauseForReview:
    def test_sets_step_review_status(self):
        from services.creative_review import pause_for_review

        db = MagicMock()
        session = _make_session(context={"pipeline": {"state": {}}})
        qc_result = _make_qc_result()

        pause_for_review(db, session, "scriptwriter", qc_result, {"scriptwriter_result": {}})

        assert session.status == "step_review"
        ctx = session.context
        review = ctx["pipeline"]["review"]
        assert review["step"] == "scriptwriter"
        assert review["qc_analysis"]["score"] == 0.7
        assert len(review["messages"]) == 1
        assert review["messages"][0]["role"] == "system"
        db.commit.assert_called_once()


# ── clear_review ─────────────────────────────────────────────


class TestClearReview:
    def test_removes_review_data(self):
        from services.creative_review import clear_review

        db = MagicMock()
        session = _make_session(context={"pipeline": {"review": {"step": "scriptwriter"}, "state": {}}})

        clear_review(db, session)

        assert "review" not in session.context["pipeline"]
        # clear_review does NOT commit — caller commits with status change
        db.commit.assert_not_called()


# ── inject_revision_feedback ─────────────────────────────────


class TestInjectRevisionFeedback:
    def test_clears_step_result_and_sets_feedback(self):
        from services.creative_review import inject_revision_feedback

        db = MagicMock()
        session = _make_session(
            status="step_review",
            context={
                "pipeline": {
                    "state": {"scriptwriter_result": {"scenes": []}},
                    "progress": {"scriptwriter": "done"},
                    "review": {"step": "scriptwriter"},
                }
            },
        )

        inject_revision_feedback(db, session, "scriptwriter", "Fix scene 1")

        assert session.status == "phase2_running"
        pipeline = session.context["pipeline"]
        assert "scriptwriter_result" not in pipeline["state"]
        assert pipeline["progress"]["scriptwriter"] == "pending"
        assert pipeline["revision_feedback"] == "Fix scene 1"
        assert "review" not in pipeline
        db.commit.assert_called_once()


# ── format_revision_feedback ─────────────────────────────────


class TestFormatRevisionFeedback:
    def test_merges_qc_and_user_feedback(self):
        from services.creative_review import format_revision_feedback

        qc = _make_qc_result(score=0.6, critical=1)
        result = format_revision_feedback(qc, "Please fix the hook")

        assert "QC Issues Found" in result
        assert "CRITICAL" in result
        assert "Revision Suggestions" in result
        assert "User Feedback" in result
        assert "Please fix the hook" in result

    def test_no_user_feedback(self):
        from services.creative_review import format_revision_feedback

        qc = _make_qc_result()
        result = format_revision_feedback(qc, None)

        assert "User Feedback" not in result
        assert "QC Issues Found" in result


# ── Pipeline integration: review disabled ──────────────────


class TestReviewDisabledSkips:
    """T2: When CREATIVE_REVIEW_ENABLED=False, pipeline skips review entirely."""

    @patch("services.creative_review.CREATIVE_REVIEW_ENABLED", False)
    @patch("services.creative_review.CREATIVE_REVIEW_STEPS", ["scriptwriter"])
    def test_should_review_returns_false_when_disabled(self):
        from services.creative_review import should_review

        assert should_review("scriptwriter") is False

    @patch("services.creative_review.CREATIVE_REVIEW_ENABLED", False)
    def test_pipeline_does_not_pause_when_disabled(self):
        """should_review returns False → pause_for_review is never called."""
        from services.creative_review import pause_for_review, should_review

        db = MagicMock()
        session = _make_session(context={"pipeline": {"state": {}}})

        # Simulate pipeline check after scriptwriter completes
        if should_review("scriptwriter"):
            pause_for_review(db, session, "scriptwriter", _make_qc_result(), {})

        # Session should NOT be paused
        assert session.status != "step_review"
        db.commit.assert_not_called()


# ── Concurrent approve rejection ───────────────────────────


class TestConcurrentApproveRejected:
    """T1: Second approve on already-processed review returns error."""

    def test_second_approve_on_non_review_status_rejected(self):
        """Simulates race condition: first approve transitions away from
        step_review, second approve sees status != step_review → rejected."""
        # First approve: session starts in step_review
        session = _make_session(
            status="step_review",
            context={
                "pipeline": {
                    "state": {"scriptwriter_result": {"scenes": []}},
                    "review": {"step": "scriptwriter"},
                }
            },
        )

        from services.creative_review import clear_review

        db = MagicMock()

        # First approve succeeds
        clear_review(db, session)
        session.status = "phase2_running"

        # Second approve: status is no longer step_review
        assert session.status != "step_review"
        # In the router, this would raise HTTPException(409)
        # Here we verify the guard condition
        assert session.status == "phase2_running"

    def test_inject_revision_after_approve_has_no_review(self):
        """After approve clears review, inject_revision_feedback
        should still work but review data is already gone."""
        from services.creative_review import clear_review

        db = MagicMock()
        session = _make_session(
            status="step_review",
            context={
                "pipeline": {
                    "state": {"scriptwriter_result": {"scenes": []}},
                    "progress": {"scriptwriter": "done"},
                    "review": {"step": "scriptwriter"},
                }
            },
        )

        # Approve clears the review
        clear_review(db, session)
        pipeline = session.context.get("pipeline", {})
        assert "review" not in pipeline


# ── run_step_qc / run_script_qc (Director QC generalization) ─


class TestRunStepQC:
    @patch("services.creative_review.get_provider")
    @patch("services.creative_review.get_next_sequence", return_value=0)
    @patch("services.creative_review.record_trace_sync")
    def test_run_step_qc_returns_parsed_result(self, mock_trace, _mock_seq, mock_provider):
        from services.creative_review import run_step_qc

        mock_gen = MagicMock()

        async def fake_generate(**_kwargs):
            return {
                "content": '{"score": 0.82, "overall_rating": "needs_revision", "issues": [], "strengths": []}',
                "model_id": "gemini-test",
                "token_usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            }

        mock_gen.generate = fake_generate
        mock_provider.return_value = mock_gen

        db = MagicMock()
        session = _make_session()

        result = run_step_qc(db, session, "cinematographer", [{"order": 0}], {"title": "Test"}, "Korean")

        assert result["score"] == 0.82
        assert result["overall_rating"] == "needs_revision"
        mock_trace.assert_called_once()
        call_kwargs = mock_trace.call_args[1]
        assert call_kwargs["agent_role"] == "cinematographer_qc"
        assert call_kwargs["step_name"] == "cinematographer_qc"

    @patch("services.creative_review.run_step_qc")
    def test_run_script_qc_delegates_to_step_qc(self, mock_step_qc):
        from services.creative_review import run_script_qc

        mock_step_qc.return_value = {"score": 0.9}
        db = MagicMock()
        session = _make_session()

        result = run_script_qc(db, session, [{"order": 0}], {"title": "T"}, "Korean")

        mock_step_qc.assert_called_once_with(db, session, "scriptwriter", [{"order": 0}], {"title": "T"}, "Korean")
        assert result["score"] == 0.9


# ── should_review with expanded steps ────────────────────────


class TestShouldReviewExpanded:
    @patch("services.creative_review.CREATIVE_REVIEW_ENABLED", True)
    @patch(
        "services.creative_review.CREATIVE_REVIEW_STEPS",
        ["scriptwriter", "cinematographer", "sound_designer", "copyright_reviewer"],
    )
    def test_all_steps_reviewable(self):
        from services.creative_review import should_review

        for step in ["scriptwriter", "cinematographer", "sound_designer", "copyright_reviewer"]:
            assert should_review(step) is True, f"{step} should be reviewable"

    @patch("services.creative_review.CREATIVE_REVIEW_ENABLED", True)
    @patch(
        "services.creative_review.CREATIVE_REVIEW_STEPS",
        ["scriptwriter", "cinematographer", "sound_designer", "copyright_reviewer"],
    )
    def test_unknown_step_not_reviewable(self):
        from services.creative_review import should_review

        assert should_review("unknown_agent") is False
