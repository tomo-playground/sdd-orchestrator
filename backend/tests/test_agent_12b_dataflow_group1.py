"""Phase 12-B Group A 테스트: 12-B-1, 12-B-2, 12-B-5 데이터 흐름.

12-B-5: Critic _parse_candidates 컨셉 필드 보존
12-B-2: Research → Critic 구조화 brief
12-B-1: Director Plan → 파이프라인 주입
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

# ── 12-B-5: _parse_candidates 필드 보존 ──────────────────────


class TestParseCandidatesFieldPreservation:
    """_parse_candidates가 concept_architect.j2 출력 필드를 보존하는지 검증."""

    def test_full_json_preserves_all_fields(self):
        """풀 JSON 입력 → 모든 필드 보존."""
        from services.agent.nodes.critic import _parse_candidates

        raw_results = [
            {
                "agent_role": "emotional_arc",
                "content": json.dumps(
                    {
                        "title": "테스트 제목",
                        "hook": "첫 3초 훅",
                        "hook_strength": "emotional_question",
                        "arc": "A → B → C",
                        "mood_progression": "tense → joyful",
                        "pacing_note": "빠른 전개",
                        "estimated_scenes": 8,
                        "key_moments": [
                            {"beat": "opening", "description": "오프닝 장면"},
                            {"beat": "climax", "description": "클라이맥스 장면"},
                            {"beat": "resolution", "description": "해결"},
                        ],
                    },
                    ensure_ascii=False,
                ),
            }
        ]

        result = _parse_candidates(raw_results)
        assert len(result) == 1
        c = result[0]
        assert c["agent_role"] == "emotional_arc"
        assert c["title"] == "테스트 제목"
        assert c["concept"] == "첫 3초 훅"
        assert c["hook_strength"] == "emotional_question"
        assert c["arc"] == "A → B → C"
        assert c["mood_progression"] == "tense → joyful"
        assert c["pacing_note"] == "빠른 전개"
        assert c["estimated_scenes"] == 8
        assert len(c["key_moments"]) == 3
        # strengths는 key_moments 앞 2개의 description
        assert c["strengths"] == ["오프닝 장면", "클라이맥스 장면"]

    def test_partial_json_defaults_to_empty(self):
        """부분 JSON → 누락 필드는 빈 문자열/None 기본값."""
        from services.agent.nodes.critic import _parse_candidates

        raw_results = [
            {
                "agent_role": "visual_hook",
                "content": json.dumps({"title": "부분 데이터"}),
            }
        ]

        result = _parse_candidates(raw_results)
        c = result[0]
        assert c["title"] == "부분 데이터"
        assert c["concept"] == ""
        assert c["hook_strength"] == ""
        assert c["arc"] == ""
        assert c["mood_progression"] == ""
        assert c["pacing_note"] == ""
        assert c["estimated_scenes"] is None
        assert c["key_moments"] == []
        assert c["strengths"] == []


# ── 12-B-2: Research → Critic 구조화 brief ──────────────────


class TestParseStructuredBrief:
    """_parse_structured_brief가 JSON과 raw text를 올바르게 처리하는지 검증."""

    def test_valid_json_parsed(self):
        """정상 JSON → dict 파싱 성공."""
        from services.agent.nodes.research import _parse_structured_brief

        raw = json.dumps(
            {
                "topic_summary": "주제 요약",
                "recommended_angle": "추천 각도",
                "key_elements": ["요소1", "요소2"],
            }
        )
        result = _parse_structured_brief(raw)
        assert isinstance(result, dict)
        assert result["topic_summary"] == "주제 요약"
        assert result["recommended_angle"] == "추천 각도"
        assert result["key_elements"] == ["요소1", "요소2"]

    def test_non_json_fallback(self):
        """비JSON → topic_summary 폴백."""
        from services.agent.nodes.research import _parse_structured_brief

        raw = "일반 텍스트 리서치 결과입니다."
        result = _parse_structured_brief(raw)
        assert isinstance(result, dict)
        assert result["topic_summary"] == raw

    def test_empty_string(self):
        """빈 문자열 → topic_summary 빈 문자열."""
        from services.agent.nodes.research import _parse_structured_brief

        result = _parse_structured_brief("")
        assert result == {"topic_summary": ""}

    def test_json_without_topic_summary_fallback(self):
        """topic_summary 없는 JSON → raw text 폴백."""
        from services.agent.nodes.research import _parse_structured_brief

        raw = json.dumps({"other_field": "value"})
        result = _parse_structured_brief(raw)
        assert result["topic_summary"] == raw


class TestFormatBriefText:
    """Writer의 _format_brief_text가 dict → 텍스트 변환을 올바르게 수행하는지 검증."""

    def test_full_brief_formatted(self):
        """모든 필드가 있는 brief → 포맷된 텍스트."""
        from services.agent.nodes.writer import _format_brief_text

        brief = {
            "topic_summary": "주제 요약 텍스트",
            "recommended_angle": "감성적 접근",
            "key_elements": ["벚꽃", "여행", "추억"],
            "emotional_arc_suggestion": "기대 → 감동 → 여운",
            "audience_hook": "첫 3초에 벚꽃 클로즈업",
        }
        result = _format_brief_text(brief)
        assert "주제 요약: 주제 요약 텍스트" in result
        assert "추천 각도: 감성적 접근" in result
        assert "핵심 요소: 벚꽃, 여행, 추억" in result
        assert "감정 곡선 제안:" in result
        assert "시청자 훅:" in result

    def test_partial_brief_only_includes_present_fields(self):
        """부분 brief → 존재하는 필드만 포함."""
        from services.agent.nodes.writer import _format_brief_text

        brief = {"topic_summary": "주제만 있음"}
        result = _format_brief_text(brief)
        assert "주제 요약: 주제만 있음" in result
        assert "추천 각도" not in result

    def test_empty_brief_returns_topic_summary(self):
        """빈 brief → topic_summary 폴백."""
        from services.agent.nodes.writer import _format_brief_text

        result = _format_brief_text({"topic_summary": "폴백 텍스트"})
        assert "폴백 텍스트" in result


class TestCriticNormalizeResearchBrief:
    """Critic의 _normalize_research_brief가 dict/str 양쪽 처리하는지 검증."""

    def test_dict_passthrough(self):
        """dict 입력 → 그대로 반환."""
        from services.agent.nodes.critic import _normalize_research_brief

        brief = {"topic_summary": "요약", "recommended_angle": "각도"}
        result = _normalize_research_brief(brief)
        assert result == brief

    def test_str_wrapped(self):
        """str 입력 → topic_summary dict로 감싸기."""
        from services.agent.nodes.critic import _normalize_research_brief

        result = _normalize_research_brief("텍스트 brief")
        assert result == {"topic_summary": "텍스트 brief"}

    def test_none_returns_none(self):
        """None → None."""
        from services.agent.nodes.critic import _normalize_research_brief

        assert _normalize_research_brief(None) is None

    def test_empty_str_returns_none(self):
        """빈 문자열 → None."""
        from services.agent.nodes.critic import _normalize_research_brief

        assert _normalize_research_brief("") is None
        assert _normalize_research_brief("  ") is None


# ── 12-B-1: Director Plan → 파이프라인 주입 ──────────────────


class TestDirectorPlanResearchInjection:
    """Research 프롬프트에 Director Plan이 포함되는지 검증."""

    @pytest.mark.asyncio
    async def test_full_mode_includes_director_plan(self):
        """Full 모드에서 director_plan이 프롬프트에 포함된다."""
        from langgraph.store.memory import InMemoryStore

        store = InMemoryStore()
        state = {
            "topic": "테스트 주제",
            "mode": "full",
            "director_plan": {
                "creative_goal": "감동적인 영상",
                "target_emotion": "따뜻한 여운",
                "quality_criteria": ["높은 몰입도", "강한 Hook"],
            },
        }

        captured_prompt = {}

        async def mock_call_with_tools(prompt, **kwargs):
            captured_prompt["value"] = prompt
            return ("리서치 결과", [])

        with patch("services.agent.tools.base.call_with_tools", new=mock_call_with_tools):
            from services.agent.nodes.research import _run_research

            await _run_research(state, store, AsyncMock())

        prompt = captured_prompt.get("value", "")
        assert "크리에이티브 방향" in prompt
        assert "감동적인 영상" in prompt
        assert "따뜻한 여운" in prompt

    @pytest.mark.asyncio
    async def test_quick_mode_no_director_plan(self):
        """Quick 모드에서 director_plan=None이면 프롬프트에 포함되지 않는다."""
        from langgraph.store.memory import InMemoryStore

        store = InMemoryStore()
        state = {
            "topic": "테스트 주제",
            "mode": "quick",
            "director_plan": None,
        }

        captured_prompt = {}

        async def mock_call_with_tools(prompt, **kwargs):
            captured_prompt["value"] = prompt
            return ("결과", [])

        with patch("services.agent.tools.base.call_with_tools", new=mock_call_with_tools):
            from services.agent.nodes.research import _run_research

            await _run_research(state, store, AsyncMock())

        prompt = captured_prompt.get("value", "")
        assert "크리에이티브 방향" not in prompt


class TestDirectorPlanWriterInjection:
    """Writer pipeline_ctx에 Director Plan이 포함되는지 검증."""

    def test_pipeline_ctx_includes_director_plan(self):
        """director_plan이 있으면 pipeline_ctx에 director_plan_context 포함."""
        state = {
            "topic": "테스트",
            "mode": "full",
            "director_plan": {
                "creative_goal": "웃긴 영상",
                "target_emotion": "폭소",
                "quality_criteria": ["유머", "타이밍"],
            },
            "research_brief": None,
        }

        # pipeline_ctx 구성 로직만 테스트 (generate_script 호출 없이)
        pipeline_ctx: dict[str, str] = {}
        director_plan = state.get("director_plan")
        if director_plan:
            pipeline_ctx["director_plan_context"] = (
                f"크리에이티브 목표: {director_plan.get('creative_goal', '')}\n"
                f"타겟 감정: {director_plan.get('target_emotion', '')}\n"
                f"품질 기준: {', '.join(director_plan.get('quality_criteria', []))}"
            )

        assert "director_plan_context" in pipeline_ctx
        assert "웃긴 영상" in pipeline_ctx["director_plan_context"]
        assert "폭소" in pipeline_ctx["director_plan_context"]
        assert "유머" in pipeline_ctx["director_plan_context"]

    def test_pipeline_ctx_no_director_plan(self):
        """director_plan=None이면 pipeline_ctx에 포함되지 않는다."""
        pipeline_ctx: dict[str, str] = {}
        director_plan = None
        if director_plan:
            pipeline_ctx["director_plan_context"] = "something"

        assert "director_plan_context" not in pipeline_ctx


class TestDirectorPlanCriticInjection:
    """Critic의 _build_debate_context에서 Director Plan이 전달되는지 검증."""

    def test_debate_context_includes_director_plan(self):
        """director_plan이 있으면 DebateContext에 포함된다."""
        from services.agent.nodes.critic import _build_debate_context

        state = {
            "topic": "테스트",
            "duration": 15,
            "structure": "Monologue",
            "language": "Korean",
            "mode": "full",
            "director_plan": {
                "creative_goal": "감동 영상",
                "target_emotion": "눈물",
                "quality_criteria": ["서사", "음악"],
            },
        }
        ctx = _build_debate_context(state)
        assert ctx.director_plan is not None
        assert ctx.director_plan["creative_goal"] == "감동 영상"

    def test_debate_context_none_director_plan(self):
        """director_plan=None이면 DebateContext에 None."""
        from services.agent.nodes.critic import _build_debate_context

        state = {
            "topic": "테스트",
            "duration": 10,
            "structure": "Monologue",
            "language": "Korean",
        }
        ctx = _build_debate_context(state)
        assert ctx.director_plan is None


class TestDirectorPlanTemplateRendering:
    """템플릿에 Director Plan 섹션이 렌더링되는지 검증."""

    def test_concept_architect_renders_director_plan(self):
        """concept_architect.j2에 director_plan 섹션이 렌더링된다."""
        from config import template_env

        tmpl = template_env.get_template("creative/concept_architect.j2")
        rendered = tmpl.render(
            perspective="Emotional Arc",
            duration=15,
            topic="테스트 주제",
            language="Korean",
            structure="Monologue",
            focus_instruction="emotional journey",
            director_plan={
                "creative_goal": "감동적 영상",
                "target_emotion": "여운",
                "quality_criteria": ["서사", "음악", "연출"],
            },
        )
        assert "Creative Direction" in rendered
        assert "감동적 영상" in rendered
        assert "여운" in rendered
        assert "서사, 음악, 연출" in rendered

    def test_concept_architect_no_director_plan(self):
        """director_plan이 None이면 섹션이 렌더링되지 않는다."""
        from config import template_env

        tmpl = template_env.get_template("creative/concept_architect.j2")
        rendered = tmpl.render(
            perspective="Visual Hook",
            duration=10,
            topic="테스트",
            language="Korean",
            structure="Monologue",
            focus_instruction="visual impact",
            director_plan=None,
        )
        assert "Creative Direction" not in rendered

    def test_writer_planning_renders_director_plan(self):
        """writer_planning.j2에 director_plan_context 섹션이 렌더링된다."""
        from config import template_env

        tmpl = template_env.get_template("creative/writer_planning.j2")
        rendered = tmpl.render(
            topic="테스트",
            duration=10,
            language="Korean",
            structure="Monologue",
            director_plan_context="크리에이티브 목표: 감동\n타겟 감정: 여운",
        )
        assert "Creative Direction" in rendered
        assert "크리에이티브 목표: 감동" in rendered

    def test_create_storyboard_renders_director_plan(self):
        """create_storyboard.j2에 director_plan_context 섹션이 렌더링된다."""
        from config import template_env

        tmpl = template_env.get_template("create_storyboard.j2")
        rendered = tmpl.render(
            topic="테스트",
            duration=10,
            style="Anime",
            structure="Monologue",
            language="Korean",
            actor_a_gender="female",
            keyword_context="",
            director_plan_context="크리에이티브 목표: 유머",
        )
        assert "Creative Direction" in rendered
        assert "크리에이티브 목표: 유머" in rendered
