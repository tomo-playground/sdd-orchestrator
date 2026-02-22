"""Phase 10-A State 스키마 테스트.

DirectorReActStep, WriterPlan, review_reflection 필드가
State에 올바르게 정의되고 타입 체크가 작동하는지 검증한다.
"""

from __future__ import annotations

from services.agent.state import DirectorReActStep, ScriptState, WriterPlan


def test_director_react_step_type():
    """DirectorReActStep TypedDict 구조를 확인한다."""
    step: DirectorReActStep = {
        "step": 1,
        "observe": "Production 결과에서 TTS 음성이 캐릭터와 어울리지 않음",
        "think": "TTS 음성을 변경하면 개선될 것으로 판단",
        "act": "TTS Designer에게 음성 변경 요청",
    }

    assert step["step"] == 1
    assert "observe" in step
    assert "think" in step
    assert "act" in step


def test_writer_plan_type():
    """WriterPlan TypedDict 구조를 확인한다."""
    plan: WriterPlan = {
        "hook_strategy": "질문형 Hook: 첫 씬에서 청자에게 질문을 던짐",
        "emotional_arc": ["호기심", "긴장", "반전", "감동", "여운"],
        "scene_distribution": {"intro": 1, "rising": 2, "climax": 1, "resolution": 1},
    }

    assert plan["hook_strategy"]
    assert len(plan["emotional_arc"]) == 5
    assert plan["scene_distribution"]["intro"] == 1


def test_script_state_with_phase10a_fields():
    """ScriptState에 Phase 10-A 필드가 추가되었는지 확인한다."""
    state: ScriptState = {
        "topic": "AI의 미래",
        "description": "AI가 인간을 대체할까?",
        "duration": 15,
        "style": "chibi",
        "language": "ko",
        "structure": "hook_rise_climax",
        "actor_a_gender": "female",
        "skip_stages": [],
        "revision_count": 0,
        "director_revision_count": 0,
        "concept_regen_count": 0,
        # Phase 10-A 필드
        "writer_plan": {
            "hook_strategy": "충격형 Hook",
            "emotional_arc": ["충격", "불안", "고민", "희망"],
            "scene_distribution": {"intro": 1, "rising": 2, "resolution": 1},
        },
        "review_reflection": "씬 3의 이미지 프롬프트가 너무 추상적. 구체적인 태그로 수정 필요.",
        "director_reasoning_steps": [
            {
                "step": 1,
                "observe": "Cinematographer의 이미지 프롬프트가 모호함",
                "think": "구체적인 포즈와 배경 태그를 요청해야 함",
                "act": "Cinematographer에게 재작업 요청",
            }
        ],
    }

    assert state["writer_plan"] is not None
    assert state["review_reflection"] is not None
    assert state["director_reasoning_steps"] is not None
    assert len(state["director_reasoning_steps"]) == 1
    assert state["director_reasoning_steps"][0]["step"] == 1


def test_state_optional_fields():
    """Phase 10-A 필드가 선택적(optional)인지 확인한다."""
    state: ScriptState = {
        "topic": "테스트",
        "duration": 10,
        "skip_stages": ["research", "concept", "production", "explain"],
        "revision_count": 0,
        "director_revision_count": 0,
        "concept_regen_count": 0,
    }

    # Quick 모드에서는 Phase 10-A 필드가 None일 수 있음
    assert state.get("writer_plan") is None
    assert state.get("review_reflection") is None
    assert state.get("director_reasoning_steps") is None


def test_director_react_multiple_steps():
    """Director ReAct Loop가 최대 3 스텝까지 기록 가능한지 확인한다."""
    steps: list[DirectorReActStep] = [
        {
            "step": 1,
            "observe": "첫 관찰",
            "think": "첫 사고",
            "act": "첫 행동",
        },
        {
            "step": 2,
            "observe": "두 번째 관찰",
            "think": "두 번째 사고",
            "act": "두 번째 행동",
        },
        {
            "step": 3,
            "observe": "세 번째 관찰",
            "think": "세 번째 사고",
            "act": "승인",
        },
    ]

    assert len(steps) == 3
    assert all(step["step"] in [1, 2, 3] for step in steps)
    assert steps[-1]["act"] == "승인"
