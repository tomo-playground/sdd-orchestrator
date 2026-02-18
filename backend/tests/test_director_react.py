"""Director ReAct Loop 테스트 (Phase 10-A).

Observe→Think→Act 루프가 최대 3 스텝까지 실행되고,
각 스텝의 reasoning이 State에 기록되는지 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.agent.nodes.director import _validate_director_react, director_node
from services.agent.state import ScriptState


@pytest.fixture
def mock_production_results():
    """Production 결과 mock 데이터."""
    return {
        "cinematographer_result": {"image_prompts": ["smile, looking_at_viewer"]},
        "tts_designer_result": {"voice_id": "voice_001"},
        "sound_designer_result": {"bgm_genre": "calm"},
        "copyright_reviewer_result": {"status": "safe"},
    }


def test_validate_director_react_success():
    """올바른 ReAct 응답이 검증을 통과한다."""
    result = {
        "observe": "모든 Production 요소가 조화롭다.",
        "think": "시각과 음성 디자인이 잘 맞는다.",
        "act": "approve",
    }
    validation = _validate_director_react(result)
    assert validation["ok"] is True
    assert not validation["issues"]


def test_validate_director_react_missing_fields():
    """필수 필드 누락 시 검증 실패."""
    result = {
        "observe": "관찰 내용",
        # think, act 누락
    }
    validation = _validate_director_react(result)
    assert validation["ok"] is False
    assert "Missing required fields" in validation["issues"][0]


def test_validate_director_react_invalid_action():
    """잘못된 act 값은 검증 실패."""
    result = {
        "observe": "관찰",
        "think": "사고",
        "act": "invalid_action",
    }
    validation = _validate_director_react(result)
    assert validation["ok"] is False
    assert "Invalid act decision" in validation["issues"][0]


def test_validate_director_react_revise_without_feedback():
    """revise_* 판정 시 feedback 필수."""
    result = {
        "observe": "관찰",
        "think": "사고",
        "act": "revise_cinematographer",
        # feedback 누락
    }
    validation = _validate_director_react(result)
    assert validation["ok"] is False
    assert "feedback required" in validation["issues"][0]


def test_validate_director_react_revise_with_feedback():
    """revise_* 판정 + feedback 포함 시 통과."""
    result = {
        "observe": "관찰",
        "think": "사고",
        "act": "revise_tts",
        "feedback": "음성을 더 밝게 변경",
    }
    validation = _validate_director_react(result)
    assert validation["ok"] is True


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_react_approve_first_step(mock_run, mock_production_results):
    """첫 스텝에서 approve 판정 시 즉시 종료한다."""
    mock_run.return_value = {
        "observe": "모든 요소가 완벽하다.",
        "think": "승인 가능하다.",
        "act": "approve",
    }

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    result = await director_node(state)

    assert result["director_decision"] == "approve"
    assert result["director_reasoning_steps"]
    assert len(result["director_reasoning_steps"]) == 1
    assert result["director_reasoning_steps"][0]["step"] == 1
    assert result["director_reasoning_steps"][0]["act"] == "approve"
    # 1회만 호출
    assert mock_run.call_count == 1


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_react_max_steps(mock_run, mock_production_results):
    """최대 3 스텝까지 실행된다."""
    # 계속 revise_* 판정
    mock_run.side_effect = [
        {
            "observe": "Step 1 관찰",
            "think": "개선 필요",
            "act": "revise_cinematographer",
            "feedback": "시각 개선 필요",
        },
        {
            "observe": "Step 2 관찰",
            "think": "여전히 개선 필요",
            "act": "revise_tts",
            "feedback": "음성 개선 필요",
        },
        {
            "observe": "Step 3 관찰",
            "think": "마지막 개선",
            "act": "revise_sound",
            "feedback": "사운드 개선 필요",
        },
    ]

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    result = await director_node(state)

    # 3번 호출 (MAX_REACT_STEPS=3)
    assert mock_run.call_count == 3
    assert len(result["director_reasoning_steps"]) == 3
    # 마지막 판정 유지
    assert result["director_decision"] == "revise_sound"
    assert result["director_feedback"] == "사운드 개선 필요"


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_react_approve_second_step(mock_run, mock_production_results):
    """두 번째 스텝에서 approve 판정 시 종료."""
    mock_run.side_effect = [
        {
            "observe": "Step 1 관찰",
            "think": "개선 필요",
            "act": "revise_cinematographer",
            "feedback": "시각 개선 필요",
        },
        {
            "observe": "Step 2 관찰",
            "think": "이제 완벽하다",
            "act": "approve",
        },
    ]

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    result = await director_node(state)

    # 2번만 호출 (두 번째 스텝에서 종료)
    assert mock_run.call_count == 2
    assert len(result["director_reasoning_steps"]) == 2
    assert result["director_decision"] == "approve"


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_react_previous_steps_context(mock_run, mock_production_results):
    """이전 스텝의 정보가 다음 스텝에 전달된다."""
    # side_effect에서 호출 시점의 template_vars를 캡처
    captured_vars = []

    async def capture_and_return(*args, **kwargs):
        # previous_steps를 deep copy로 캡처 (mutable 리스트 문제 회피)
        captured_vars.append(list(kwargs["template_vars"].get("previous_steps", [])))
        # 첫 호출
        if len(captured_vars) == 1:
            return {
                "observe": "Step 1 관찰",
                "think": "개선 필요",
                "act": "revise_cinematographer",
                "feedback": "시각 개선",
            }
        # 두 번째 호출
        return {
            "observe": "Step 2 관찰",
            "think": "승인",
            "act": "approve",
        }

    mock_run.side_effect = capture_and_return

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    await director_node(state)

    # 첫 호출 시 previous_steps는 빈 리스트
    assert len(captured_vars[0]) == 0
    # 두 번째 호출 시 previous_steps에 첫 스텝 정보가 포함됨
    assert len(captured_vars[1]) == 1
    assert captured_vars[1][0]["step"] == 1


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_react_error_fallback(mock_run, mock_production_results):
    """에러 발생 시 approve fallback 처리."""
    mock_run.side_effect = Exception("Gemini API 에러")

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    result = await director_node(state)

    # 에러 시 approve fallback
    assert result["director_decision"] == "approve"
    assert "평가 실패" in result["director_feedback"]
    # reasoning_steps는 빈 리스트
    assert result["director_reasoning_steps"] == []
