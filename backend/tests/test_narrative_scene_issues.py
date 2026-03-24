"""Narrative per-scene 이슈 평가 테스트 (SP-064).

NarrativeScoreOutput에 scene_issues 필드를 추가하고,
Revise 노드에 씬별 구체적 피드백을 전달하는 전체 흐름을 검증한다.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.llm_models import NarrativeScoreOutput
from services.agent.nodes.review import _build_narrative_score
from services.agent.nodes.revise import _build_feedback

# ── DoD 1: NarrativeScoreOutput scene_issues 필드 ──


class TestNarrativeScoreOutputSceneIssues:
    """NarrativeScoreOutput에 scene_issues 필드가 올바르게 동작한다."""

    def test_scene_issues_included_in_narrative_score(self):
        """scene_issues가 NarrativeScore TypedDict에 전달된다."""
        parsed = NarrativeScoreOutput(
            hook=0.8,
            emotional_arc=0.7,
            twist_payoff=0.6,
            speaker_tone=0.7,
            script_image_sync=0.8,
            spoken_naturalness=0.7,
            retention_flow=0.7,
            pacing_rhythm=0.7,
            feedback="좋은 스크립트입니다.",
            scene_issues=[
                {"scene_id": 3, "issue": "Hook이 약함", "dimension": "hook", "severity": "error"},
            ],
        )
        score = _build_narrative_score(parsed)
        assert score["scene_issues"] == [
            {"scene_id": 3, "issue": "Hook이 약함", "dimension": "hook", "severity": "error"},
        ]

    def test_scene_issues_default_empty(self):
        """scene_issues 미지정 시 빈 배열이 기본값이다."""
        parsed = NarrativeScoreOutput(
            hook=0.5,
            emotional_arc=0.5,
            twist_payoff=0.5,
            speaker_tone=0.5,
            script_image_sync=0.5,
            spoken_naturalness=0.5,
            retention_flow=0.5,
            pacing_rhythm=0.5,
        )
        score = _build_narrative_score(parsed)
        assert score["scene_issues"] == []


# ── DoD 4: Revise _build_feedback()에서 scene_issues 파싱 ──


class TestBuildFeedbackSceneIssues:
    """_build_feedback()가 scene_issues를 씬별 피드백으로 변환한다."""

    def test_scene_issues_error_and_warning(self):
        """error + warning 혼합 scene_issues가 피드백에 포함된다."""
        state = {
            "review_result": {
                "errors": [],
                "narrative_score": {
                    "overall": 0.5,
                    "feedback": "개선 필요",
                    "scene_issues": [
                        {"scene_id": 1, "issue": "Hook이 일반적인 서술", "dimension": "hook", "severity": "error"},
                        {"scene_id": 3, "issue": "전환 어색함", "dimension": "transition", "severity": "warning"},
                    ],
                },
            },
        }
        feedback = _build_feedback(state)
        assert "[씬별 서사 이슈]" in feedback
        assert "씬 1 (hook) [ERROR]" in feedback
        assert "Hook이 일반적인 서술" in feedback
        assert "씬 3 (transition) [WARN]" in feedback
        assert "전환 어색함" in feedback

    def test_empty_scene_issues_no_section(self):
        """빈 scene_issues → [씬별 서사 이슈] 섹션이 출력되지 않는다."""
        state = {
            "review_result": {
                "errors": [],
                "narrative_score": {
                    "overall": 0.8,
                    "feedback": "좋습니다",
                    "scene_issues": [],
                },
            },
        }
        feedback = _build_feedback(state)
        assert "[씬별 서사 이슈]" not in feedback

    def test_no_scene_issues_legacy(self):
        """scene_issues 키 없는 레거시 state → 기존 동작 동일."""
        state = {
            "review_result": {
                "errors": ["씬 개수 부족"],
                "narrative_score": {
                    "overall": 0.6,
                    "feedback": "Hook 약함",
                },
            },
        }
        feedback = _build_feedback(state)
        assert "[씬별 서사 이슈]" not in feedback
        assert "[서사 품질 피드백] Hook 약함" in feedback
        assert "[검증 오류]" in feedback


# ── DoD 5: 통합 호출 mock으로 scene_issues 파싱 검증 ──


def _make_unified_json_with_scene_issues(scene_issues=None):
    """통합 응답 JSON 생성 헬퍼 (scene_issues 포함)."""
    narr = {
        "hook": 0.4,
        "emotional_arc": 0.6,
        "twist_payoff": 0.5,
        "speaker_tone": 0.7,
        "script_image_sync": 0.6,
        "spoken_naturalness": 0.5,
        "retention_flow": 0.5,
        "pacing_rhythm": 0.5,
        "feedback": "Hook 개선 필요",
        "scene_issues": scene_issues or [],
    }
    return json.dumps(
        {
            "technical": {
                "overall_score": 0.85,
                "passed": True,
                "feedback": "",
                "scene_issues": [],
            },
            "narrative": narr,
            "reflection": {
                "root_cause": "Hook 약함",
                "impact": "시청자 이탈",
                "strategy": "질문형 변경",
                "expected_outcome": "개선 기대",
            },
        }
    )


def _full_state(scene_count=5, duration=10):
    """테스트용 Full 모드 state."""
    return {
        "draft_scenes": [
            {"scene_id": i, "script": f"테스트 씬 {i}", "speaker": "speaker_1", "duration": 2, "image_prompt": "smile"}
            for i in range(1, scene_count + 1)
        ],
        "duration": duration,
        "language": "korean",
        "structure": "monologue",
        "topic": "테스트 주제",
        "skip_stages": [],
    }


@pytest.mark.asyncio
@patch("services.agent.nodes.review.get_llm_provider")
@patch("services.agent.langfuse_prompt.compile_prompt")
async def test_unified_narrative_scene_issues_parsed(mock_compile, mock_llm_provider):
    """통합 호출 응답의 narrative.scene_issues가 review_result에 전달된다."""
    from services.agent.nodes.review import review_node

    mock_compiled = MagicMock()
    mock_compiled.system = "system"
    mock_compiled.user = "prompt"
    mock_compiled.langfuse_prompt = None
    mock_compile.return_value = mock_compiled

    scene_issues = [
        {"scene_id": 1, "issue": "Hook이 약함", "dimension": "hook", "severity": "error"},
        {"scene_id": 4, "issue": "전환 어색", "dimension": "transition", "severity": "warning"},
    ]

    mock_llm_resp = MagicMock()
    mock_llm_resp.text = _make_unified_json_with_scene_issues(scene_issues)
    mock_llm_resp.observation_id = "obs-123"
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_llm_resp)
    mock_llm_provider.return_value = mock_provider

    result = await review_node(_full_state())

    ns = result["review_result"]["narrative_score"]
    assert ns["scene_issues"] == scene_issues


# ── DoD 5: Revise Tier 3에서 pipeline_context에 씬 번호 피드백 전달 ──


@pytest.mark.asyncio
@patch("services.agent.nodes.revise.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.revise.get_db_session")
async def test_revise_tier3_passes_scene_feedback(mock_db, mock_gen_script):
    """Tier 3 재생성 시 pipeline_context에 씬 번호가 포함된 피드백이 전달된다."""
    from services.agent.nodes.revise import revise_node

    mock_db.return_value.__enter__ = MagicMock()
    mock_db.return_value.__exit__ = MagicMock(return_value=False)

    mock_gen_script.return_value = {
        "scenes": [
            {"scene_id": 1, "script": "새 씬 1", "speaker": "speaker_1", "duration": 3, "image_prompt": "p"},
        ],
    }

    state = {
        "revision_count": 0,
        "draft_scenes": [
            {"scene_id": 1, "script": "기존 씬", "speaker": "speaker_1", "duration": 3, "image_prompt": "p"},
        ],
        "review_result": {
            "errors": ["복잡한 에러"],
            "narrative_score": {
                "overall": 0.4,
                "feedback": "Hook 약함",
                "scene_issues": [
                    {"scene_id": 1, "issue": "Hook이 일반적", "dimension": "hook", "severity": "error"},
                ],
            },
        },
        "topic": "테스트",
        "duration": 10,
        "language": "korean",
        "structure": "monologue",
        "style": "Anime",
        "actor_a_gender": "female",
        "revision_history": [],
        "review_reflection": None,
        "best_narrative_score": 0.0,
    }

    await revise_node(state)

    # generate_script가 호출되었는지 확인
    assert mock_gen_script.called
    call_kwargs = mock_gen_script.call_args
    pipeline_ctx = call_kwargs.kwargs.get("pipeline_context") or call_kwargs[1].get("pipeline_context", {})
    feedback_text = pipeline_ctx.get("revision_feedback", "")
    assert "씬 1 (hook) [ERROR]" in feedback_text
    assert "Hook이 일반적" in feedback_text
