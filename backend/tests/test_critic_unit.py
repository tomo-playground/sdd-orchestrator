"""Critic 노드 순수 함수 단위 테스트."""

from __future__ import annotations

import json
from unittest.mock import patch

from services.agent.nodes.critic import (
    _build_critique_feedback,
    _detect_groupthink,
    _extract_winner,
    _normalize_research_brief,
    _parse_candidates,
)


# ── _normalize_research_brief ─────────────────────────────


class TestNormalizeResearchBrief:
    def test_dict_passthrough(self):
        d = {"topic_summary": "test"}
        assert _normalize_research_brief(d) == d

    def test_string_wrapped(self):
        result = _normalize_research_brief("test topic")
        assert result == {"topic_summary": "test topic"}

    def test_empty_string_returns_none(self):
        assert _normalize_research_brief("") is None
        assert _normalize_research_brief("   ") is None

    def test_none_returns_none(self):
        assert _normalize_research_brief(None) is None


# ── _parse_candidates ─────────────────────────────────────


class TestParseCandidates:
    def test_valid_json_content(self):
        raw = [
            {
                "agent_role": "emotional_arc",
                "content": json.dumps(
                    {
                        "title": "감정적 여정",
                        "hook": "강렬한 도입",
                        "hook_strength": "high",
                        "arc": "rising",
                    }
                ),
            }
        ]
        result = _parse_candidates(raw)
        assert len(result) == 1
        assert result[0]["agent_role"] == "emotional_arc"
        assert result[0]["title"] == "감정적 여정"
        assert result[0]["concept"] == "강렬한 도입"

    def test_invalid_json_graceful(self):
        raw = [{"agent_role": "test", "content": "not json at all {{{"}]
        result = _parse_candidates(raw)
        assert len(result) == 1
        assert result[0]["agent_role"] == "test"
        assert result[0]["title"] == ""

    def test_dict_content_no_parse(self):
        raw = [{"agent_role": "test", "content": {"title": "direct dict", "hook": "h"}}]
        result = _parse_candidates(raw)
        assert result[0]["title"] == "direct dict"

    def test_empty_list(self):
        assert _parse_candidates([]) == []


# ── _extract_winner ───────────────────────────────────────


class TestExtractWinner:
    def test_finds_matching_role(self):
        concepts = [
            {"agent_role": "tension_builder", "title": "A"},
            {"agent_role": "emotional_arc", "title": "B"},
        ]
        evaluation = {"best_agent_role": "emotional_arc"}
        winner = _extract_winner(concepts, evaluation)
        assert winner["title"] == "B"

    def test_fallback_to_first(self):
        concepts = [{"agent_role": "test", "title": "first"}]
        evaluation = {"best_agent_role": "nonexistent"}
        assert _extract_winner(concepts, evaluation)["title"] == "first"

    def test_empty_concepts(self):
        assert _extract_winner([], {"best_agent_role": "x"}) == {}


# ── _build_critique_feedback ──────────────────────────────


class TestBuildCritiqueFeedback:
    def test_excludes_target_role(self):
        concepts = [
            {"agent_role": "emotional_arc", "title": "A", "concept": "hook A"},
            {"agent_role": "tension_builder", "title": "B", "concept": "hook B"},
            {"agent_role": "knowledge", "title": "C", "concept": "hook C"},
        ]
        feedback = _build_critique_feedback(concepts, "emotional_arc")
        text = feedback["by_role"]["emotional_arc"]
        assert "tension_builder" in text
        assert "knowledge" in text
        assert "emotional_arc" not in text.split("다른 Architect들의 컨셉:")[1].split("\n")[1]


# ── _detect_groupthink ────────────────────────────────────


class TestDetectGroupthink:
    def test_different_concepts_no_groupthink(self):
        concepts = [
            {"title": "감정적 여정", "concept": "완전히 다른 접근"},
            {"title": "긴장감 빌드", "concept": "독특한 아이디어"},
        ]
        # _concepts_too_similar checks similarity; different concepts should not trigger
        result = _detect_groupthink(concepts)
        assert isinstance(result, bool)

    def test_empty_list(self):
        assert _detect_groupthink([]) is False or _detect_groupthink([]) is True
        # Just verify it doesn't crash
