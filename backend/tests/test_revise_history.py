"""Revise 노드 — _append_history 테스트."""

from __future__ import annotations

from services.agent.nodes.revise import _append_history


class TestAppendHistory:
    """_append_history: revision_history entry 누적 로직."""

    def _state(self, **kwargs) -> dict:
        return {
            "revision_history": [],
            "review_result": {},
            "review_reflection": None,
            "director_checkpoint_score": None,
            **kwargs,
        }

    def test_basic_entry_structure(self):
        """기본 entry 필드가 올바르게 채워진다."""
        state = self._state(
            review_result={"errors": ["씬 개수 부족"], "warnings": [], "passed": False},
            review_reflection="근본 원인: ...",
            director_checkpoint_score=0.82,
        )
        history = _append_history(state)
        assert len(history) == 1
        entry = history[0]
        assert entry["attempt"] == 1
        assert entry["errors"] == ["씬 개수 부족"]
        assert entry["warnings"] == []
        assert entry["reflection"] == "근본 원인: ..."
        assert entry["score"] == 0.82
        assert entry["tier"] == "pending"

    def test_warnings_included(self):
        """warnings 필드가 entry에 포함된다."""
        state = self._state(
            review_result={"errors": [], "warnings": ["감정 호 단조로움"], "passed": True},
        )
        history = _append_history(state)
        assert history[0]["warnings"] == ["감정 호 단조로움"]

    def test_narrative_score_included_when_present(self):
        """narrative_score가 있으면 overall + feedback이 entry에 포함된다."""
        state = self._state(
            review_result={
                "errors": [],
                "warnings": [],
                "passed": True,
                "narrative_score": {"overall": 0.62, "feedback": "서사 흐름이 단조롭습니다."},
            },
        )
        history = _append_history(state)
        ns = history[0].get("narrative_score")
        assert ns is not None
        assert ns["overall"] == 0.62
        assert ns["feedback"] == "서사 흐름이 단조롭습니다."

    def test_narrative_score_omitted_when_absent(self):
        """narrative_score 없으면 entry에 포함되지 않는다."""
        state = self._state(
            review_result={"errors": ["오류"], "warnings": [], "passed": False},
        )
        history = _append_history(state)
        assert "narrative_score" not in history[0]

    def test_attempt_increments(self):
        """기존 이력이 있으면 attempt가 누적 증가한다."""
        existing = [{"attempt": 1, "tier": "rule_fix"}]
        state = self._state(revision_history=existing)
        history = _append_history(state)
        assert history[-1]["attempt"] == 2

    def test_empty_review_result_defaults(self):
        """review_result가 없어도 빈 errors/warnings로 처리된다."""
        state = self._state(review_result=None)
        history = _append_history(state)
        assert history[0]["errors"] == []
        assert history[0]["warnings"] == []
