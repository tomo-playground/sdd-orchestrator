"""Tests for creative_utils.py — pipeline_log, build_template_vars, finalize_pipeline, hints."""

from __future__ import annotations

from unittest.mock import MagicMock


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


def _base_context() -> dict:
    return {
        "selected_concept": {"title": "Test", "hook": "Hook"},
        "duration": 30,
        "structure": "Monologue",
        "language": "Korean",
        "character_name": "하루",
        "characters": {"A": {"id": 1, "name": "하루", "tags": ["1girl"]}},
        "disabled_steps": [],
        "pipeline": {"state": {}, "progress": {}, "logs": []},
    }


# ── pipeline_log ─────────────────────────────────────────────


class TestPipelineLog:
    def test_appends_log_entry(self):
        from services.creative_utils import pipeline_log

        db = MagicMock()
        session = _make_session(context={"pipeline": {"logs": []}})

        pipeline_log(db, session, "scriptwriter", "Generating scripts...")

        logs = session.context["pipeline"]["logs"]
        assert len(logs) == 1
        assert logs[0]["step"] == "scriptwriter"
        assert logs[0]["msg"] == "Generating scripts..."
        assert logs[0]["level"] == "info"
        assert "ts" in logs[0]
        db.commit.assert_called_once()

    def test_appends_to_existing_logs(self):
        from services.creative_utils import pipeline_log

        db = MagicMock()
        existing = [{"ts": "2026-01-01T00:00:00", "step": "x", "msg": "old", "level": "info"}]
        session = _make_session(context={"pipeline": {"logs": existing}})

        pipeline_log(db, session, "cinematographer", "Done", "info")

        logs = session.context["pipeline"]["logs"]
        assert len(logs) == 2
        assert logs[1]["step"] == "cinematographer"

    def test_error_level(self):
        from services.creative_utils import pipeline_log

        db = MagicMock()
        session = _make_session(context={"pipeline": {"logs": []}})

        pipeline_log(db, session, "pipeline", "Something failed", "error")

        logs = session.context["pipeline"]["logs"]
        assert logs[0]["level"] == "error"

    def test_creates_pipeline_if_missing(self):
        from services.creative_utils import pipeline_log

        db = MagicMock()
        session = _make_session(context={})

        pipeline_log(db, session, "scriptwriter", "Starting...")

        assert "pipeline" in session.context
        assert len(session.context["pipeline"]["logs"]) == 1


# ── build_template_vars ──────────────────────────────────────


class TestBuildTemplateVars:
    def test_scriptwriter_vars(self):
        from services.creative_utils import build_template_vars

        ctx = _base_context()
        chars = ctx["characters"]

        result = build_template_vars("scriptwriter", {}, ctx, chars)

        assert result["concept"] == ctx["selected_concept"]
        assert result["duration"] == 30
        assert result["structure"] == "Monologue"
        assert result["language"] == "Korean"
        assert result["characters"] == chars
        assert result["min_scenes"] == 6  # max(4, 30 // 5)
        assert result["max_scenes"] == 15  # 30 // 2
        assert "script_length_hint" in result
        assert "scene_duration_hint" in result
        assert result["feedback"] is None

    def test_scriptwriter_with_revision_feedback(self):
        from services.creative_utils import build_template_vars

        ctx = _base_context()
        result = build_template_vars("scriptwriter", {}, ctx, {}, revision_fb="Fix hook")

        assert result["feedback"] == "Fix hook"

    def test_cinematographer_vars(self):
        from services.creative_utils import build_template_vars

        ctx = _base_context()
        chars = ctx["characters"]
        state = {"scriptwriter_result": {"scenes": [{"order": 0, "script": "Test"}]}}

        result = build_template_vars("cinematographer", state, ctx, chars)

        assert result["scenes"] == [{"order": 0, "script": "Test"}]
        assert "characters_tags" in result

    def test_sound_designer_vars(self):
        from services.creative_utils import build_template_vars

        ctx = _base_context()
        state = {"cinematographer_result": {"scenes": [{"order": 0}]}}

        result = build_template_vars("sound_designer", state, ctx, {})

        assert result["scenes"] == [{"order": 0}]
        assert result["duration"] == 30
        assert "concept" in result

    def test_copyright_reviewer_vars(self):
        from services.creative_utils import build_template_vars

        ctx = _base_context()
        state = {"cinematographer_result": {"scenes": [{"order": 0}]}}

        result = build_template_vars("copyright_reviewer", state, ctx, {})

        assert result["scenes"] == [{"order": 0}]

    def test_unknown_step_returns_empty(self):
        from services.creative_utils import build_template_vars

        result = build_template_vars("unknown_step", {}, {}, {})
        assert result == {}


# ── finalize_pipeline ────────────────────────────────────────


class TestFinalizePipeline:
    def test_finalize_with_all_results(self):
        from services.creative_utils import finalize_pipeline

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = [0]

        session = _make_session(context={"pipeline": {"state": {}}})
        state = {
            "scriptwriter_result": {"scenes": [{"order": 0}]},
            "cinematographer_result": {"scenes": [{"order": 0, "camera": "close_up"}]},
            "sound_designer_result": {"recommendation": {"prompt": "calm"}},
            "copyright_reviewer_result": {"checks": []},
        }

        finalize_pipeline(db, session, state)

        assert session.status == "completed"
        assert session.final_output["scenes"] == [{"order": 0, "camera": "close_up"}]
        assert session.final_output["music_recommendation"] == {"prompt": "calm"}
        db.commit.assert_called_once()

    def test_finalize_with_skipped_sound_designer(self):
        """When sound_designer is skipped, music_recommendation is None."""
        from services.creative_utils import finalize_pipeline

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = [0]

        session = _make_session(context={"pipeline": {"state": {}}})
        state = {
            "scriptwriter_result": {"scenes": [{"order": 0}]},
            "cinematographer_result": {"scenes": [{"order": 0}]},
        }

        finalize_pipeline(db, session, state)

        assert session.status == "completed"
        assert session.final_output["music_recommendation"] is None
        assert len(session.final_output["scenes"]) == 1


# ── _script_length_hint ──────────────────────────────────────


class TestScriptLengthHint:
    def test_korean_hint(self):
        from services.creative_utils import _script_length_hint

        result = _script_length_hint("Korean")
        assert "characters" in result
        assert "Korean" in result

    def test_english_hint(self):
        from services.creative_utils import _script_length_hint

        result = _script_length_hint("English")
        assert "words" in result
        assert "English" in result
