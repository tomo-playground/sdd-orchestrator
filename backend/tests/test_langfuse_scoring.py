"""Phase 38: LangFuse Scoring -- 노드별 record_score 호출 검증.

각 노드에서 record_score가 올바른 Score name으로 호출되는지
정적 검증(import 존재, 소스코드 패턴)으로 확인한다.

노드 전체 실행은 의존성(LLM, DB, state)이 많아 단위 테스트에 부적합하므로,
inspect.getsource() 기반의 가벼운 검증으로 접근한다.
"""

from __future__ import annotations

import inspect
import re


def _has_record_score_call(source: str, score_name: str) -> bool:
    """소스 코드에서 record_score("score_name"...) 호출을 찾는다.

    줄바꿈이 포함된 멀티라인 호출도 매칭한다.
    예: record_score(\n    "narrative_overall", ...)
    """
    pattern = rf'record_score\(\s*"{re.escape(score_name)}"'
    return bool(re.search(pattern, source))


# ── Score Config 일관성 검증 ──────────────────────────────────


class TestScoreConfigConsistency:
    """LANGFUSE_SCORE_CONFIGS에 정의된 Score name이 노드 코드에 존재하는지 검증."""

    def test_all_score_names_defined_in_config(self):
        """노드에서 사용하는 Score name이 모두 config에 등록되어 있는지 확인."""
        from config_pipelines import LANGFUSE_SCORE_CONFIGS

        expected_names = {
            "first_pass",
            "revision_count",
            "scene_count",
            "visual_qc_issues",
            "script_qc_issues",
            "research_quality",
            "director_revision_count",
            "pipeline_duration_sec",
            "narrative_overall",
        }
        assert expected_names == set(LANGFUSE_SCORE_CONFIGS.keys())

    def test_first_pass_is_boolean(self):
        from config_pipelines import LANGFUSE_SCORE_CONFIGS

        assert LANGFUSE_SCORE_CONFIGS["first_pass"]["data_type"] == "BOOLEAN"

    def test_numeric_scores_have_correct_type(self):
        from config_pipelines import LANGFUSE_SCORE_CONFIGS

        numeric_names = [
            "revision_count",
            "scene_count",
            "visual_qc_issues",
            "script_qc_issues",
            "research_quality",
            "director_revision_count",
            "pipeline_duration_sec",
            "narrative_overall",
        ]
        for name in numeric_names:
            assert LANGFUSE_SCORE_CONFIGS[name]["data_type"] == "NUMERIC", (
                f"{name} should be NUMERIC"
            )


# ── Import 존재 검증 ─────────────────────────────────────────


class TestScoringImports:
    """각 노드에서 record_score를 올바르게 import하는지 검증."""

    def test_review_imports_record_score(self):
        from services.agent.nodes import review

        assert hasattr(review, "record_score")

    def test_finalize_imports_record_score(self):
        from services.agent.nodes import finalize

        assert hasattr(finalize, "record_score")

    def test_cinematographer_imports_record_score(self):
        from services.agent.nodes import cinematographer

        assert hasattr(cinematographer, "record_score")

    def test_research_imports_record_score(self):
        from services.agent.nodes import research

        assert hasattr(research, "record_score")

    def test_director_imports_record_score(self):
        from services.agent.nodes import director

        assert hasattr(director, "record_score")

    def test_finalize_imports_get_pipeline_elapsed(self):
        from services.agent.nodes import finalize

        assert hasattr(finalize, "get_pipeline_elapsed_sec")


# ── record_score 호출 패턴 검증 (Review 노드) ────────────────


class TestReviewScorePatterns:
    """Review 노드의 record_score 호출 패턴 검증."""

    def _get_review_source(self) -> str:
        from services.agent.nodes import review

        return inspect.getsource(review)

    def test_records_first_pass(self):
        source = self._get_review_source()
        assert _has_record_score_call(source, "first_pass")

    def test_records_script_qc_issues(self):
        source = self._get_review_source()
        assert _has_record_score_call(source, "script_qc_issues")

    def test_records_narrative_overall(self):
        source = self._get_review_source()
        assert _has_record_score_call(source, "narrative_overall")

    def test_narrative_overall_passes_comment(self):
        """narrative_overall은 JSON comment와 함께 기록된다."""
        source = self._get_review_source()
        # record_score("narrative_overall", ..., comment=...) 패턴 확인
        assert "comment=" in source


# ── record_score 호출 패턴 검증 (Finalize 노드) ──────────────


class TestFinalizeScorePatterns:
    """Finalize 노드의 record_score 호출 패턴 검증."""

    def _get_finalize_source(self) -> str:
        from services.agent.nodes import finalize

        return inspect.getsource(finalize)

    def test_records_revision_count(self):
        source = self._get_finalize_source()
        assert _has_record_score_call(source, "revision_count")

    def test_records_scene_count(self):
        source = self._get_finalize_source()
        assert _has_record_score_call(source, "scene_count")

    def test_records_pipeline_duration_sec(self):
        source = self._get_finalize_source()
        assert _has_record_score_call(source, "pipeline_duration_sec")

    def test_pipeline_duration_uses_helper(self):
        """pipeline_duration_sec는 get_pipeline_elapsed_sec()를 사용한다."""
        source = self._get_finalize_source()
        assert "get_pipeline_elapsed_sec()" in source


# ── record_score 호출 패턴 검증 (Cinematographer 노드) ────────


class TestCinematographerScorePatterns:
    """Cinematographer 노드의 record_score 호출 패턴 검증."""

    def _get_source(self) -> str:
        from services.agent.nodes import cinematographer

        return inspect.getsource(cinematographer)

    def test_records_visual_qc_issues(self):
        source = self._get_source()
        assert _has_record_score_call(source, "visual_qc_issues")

    def test_visual_qc_counts_issues(self):
        """visual_qc_issues는 len(qc.get("issues"...)) 패턴으로 카운트한다."""
        source = self._get_source()
        assert 'len(qc.get("issues"' in source


# ── record_score 호출 패턴 검증 (Research 노드) ──────────────


class TestResearchScorePatterns:
    """Research 노드의 record_score 호출 패턴 검증."""

    def _get_source(self) -> str:
        from services.agent.nodes import research

        return inspect.getsource(research)

    def test_records_research_quality(self):
        source = self._get_source()
        assert _has_record_score_call(source, "research_quality")

    def test_research_quality_uses_score_overall(self):
        """research_quality는 score.get("overall") 값을 사용한다."""
        source = self._get_source()
        assert 'score.get("overall")' in source


# ── record_score 호출 패턴 검증 (Director 노드) ──────────────


class TestDirectorScorePatterns:
    """Director 노드의 record_score 호출 패턴 검증."""

    def _get_source(self) -> str:
        from services.agent.nodes import director

        return inspect.getsource(director)

    def test_records_director_revision_count(self):
        source = self._get_source()
        assert _has_record_score_call(source, "director_revision_count")


# ── FastTrack 모드 최소 Score 보장 ────────────────────────────


class TestFastTrackScoring:
    """FastTrack 모드에서 최소 3개 Score 기록 보장 검증.

    Finalize는 Full/FastTrack 무관하게 항상 실행되므로,
    revision_count, scene_count, pipeline_duration_sec는 반드시 기록된다.
    """

    def test_finalize_always_records_three_scores(self):
        from services.agent.nodes import finalize

        source = inspect.getsource(finalize)
        assert _has_record_score_call(source, "revision_count")
        assert _has_record_score_call(source, "scene_count")
        assert _has_record_score_call(source, "pipeline_duration_sec")


# ── 노드-Score 매핑 완전성 검증 ──────────────────────────────


class TestNodeScoreMapping:
    """각 Score name이 정확히 하나 이상의 노드에서 기록되는지 검증."""

    def _collect_all_node_sources(self) -> str:
        from services.agent.nodes import (
            cinematographer,
            director,
            finalize,
            research,
            review,
        )

        return "\n".join(
            inspect.getsource(mod)
            for mod in [review, finalize, cinematographer, research, director]
        )

    def test_every_config_score_has_recording_node(self):
        """LANGFUSE_SCORE_CONFIGS의 모든 Score가 최소 1개 노드에서 기록된다."""
        from config_pipelines import LANGFUSE_SCORE_CONFIGS

        all_sources = self._collect_all_node_sources()
        for name in LANGFUSE_SCORE_CONFIGS:
            assert _has_record_score_call(all_sources, name), (
                f"Score '{name}' is defined in config but no node records it"
            )
