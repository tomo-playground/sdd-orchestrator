"""Director ReAct Loop 테스트 (Phase 10-A).

Observe→Think→Act 루프가 최대 3 스텝까지 실행되고,
각 스텝의 reasoning이 State에 기록되는지 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.agent.llm_models import DirectorReActOutput, validate_with_model
from services.agent.nodes.director import director_node
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
    validation = validate_with_model(DirectorReActOutput, result)
    assert validation.ok is True
    assert not validation.issues


def test_validate_director_react_missing_fields():
    """필수 필드 누락 시 검증 실패."""
    result = {
        "observe": "관찰 내용",
        # think, act 누락
    }
    validation = validate_with_model(DirectorReActOutput, result)
    assert validation.ok is False
    assert len(validation.issues) > 0


def test_validate_director_react_invalid_action():
    """잘못된 act 값은 검증 실패."""
    result = {
        "observe": "관찰",
        "think": "사고",
        "act": "invalid_action",
    }
    validation = validate_with_model(DirectorReActOutput, result)
    assert validation.ok is False
    assert len(validation.issues) > 0


def test_validate_director_react_revise_without_feedback():
    """revise_* 판정 시 feedback 필수."""
    result = {
        "observe": "관찰",
        "think": "사고",
        "act": "revise_cinematographer",
        # feedback 누락
    }
    validation = validate_with_model(DirectorReActOutput, result)
    assert validation.ok is False
    assert any("feedback" in issue for issue in validation.issues)


def test_validate_director_react_revise_with_feedback():
    """revise_* 판정 + feedback 포함 시 통과."""
    result = {
        "observe": "관찰",
        "think": "사고",
        "act": "revise_tts",
        "feedback": "음성을 더 밝게 변경",
    }
    validation = validate_with_model(DirectorReActOutput, result)
    assert validation.ok is True


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

    result = await director_node(state, {})

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

    result = await director_node(state, {})

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

    result = await director_node(state, {})

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

    await director_node(state, {})

    # 첫 호출 시 previous_steps는 빈 리스트
    assert len(captured_vars[0]) == 0
    # 두 번째 호출 시 previous_steps에 첫 스텝 정보가 포함됨
    assert len(captured_vars[1]) == 1
    assert captured_vars[1][0]["step"] == 1


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_react_error_fallback(mock_run, mock_production_results):
    """에러 발생 시 재시도 후 error 결정 반환 (자동 통과 제거)."""
    mock_run.side_effect = Exception("Gemini API 에러")

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    result = await director_node(state, {})

    # 양쪽 실패 시 error 결정
    assert result["director_decision"] == "error"
    assert "평가 불가" in result["director_feedback"]
    # reasoning_steps는 빈 리스트
    assert result["director_reasoning_steps"] == []


# ── Phase 10-C-2: 양방향 소통 통합 테스트 ────────────────


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_agent_with_message", new_callable=AsyncMock)
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_bidirectional_communication(
    mock_run_production,
    mock_run_agent,
    mock_production_results,
):
    """Director가 Production Agent와 양방향 소통을 한다."""
    # Director가 Step 1에서 revise, Step 2에서 approve
    mock_run_production.side_effect = [
        {
            "observe": "씬 1의 카메라 앵글이 부적절하다.",
            "think": "close-up으로 변경 필요",
            "act": "revise_cinematographer",
            "feedback": "씬 1의 카메라 앵글을 close-up으로 변경하세요",
        },
        {
            "observe": "이제 완벽하다",
            "think": "승인 가능",
            "act": "approve",
        },
    ]

    # Cinematographer Agent가 응답
    updated_cinematographer_result = {"scenes": [{"order": 1, "camera": "close-up"}]}
    response_message = {
        "sender": "cinematographer",
        "recipient": "director",
        "content": "씬 1의 카메라 앵글을 close-up으로 변경했습니다. 감정 표현을 강화하기 위함입니다.",
        "message_type": "approval",
        "metadata": {"result": updated_cinematographer_result},
    }
    mock_run_agent.return_value = (updated_cinematographer_result, response_message)

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    result = await director_node(state, {})

    # Agent 메시지 호출 확인
    assert mock_run_agent.call_count == 1
    call_args = mock_run_agent.call_args
    assert call_args.kwargs["target_agent"] == "cinematographer"
    assert call_args.kwargs["message"]["content"] == "씬 1의 카메라 앵글을 close-up으로 변경하세요"

    # agent_messages가 state에 기록되었는지 확인
    assert "agent_messages" in result
    agent_messages = result["agent_messages"]
    assert len(agent_messages) == 2  # Director → Agent, Agent → Director

    # Director의 피드백 메시지
    assert agent_messages[0]["sender"] == "director"
    assert agent_messages[0]["recipient"] == "cinematographer"
    assert agent_messages[0]["message_type"] == "feedback"

    # Agent의 응답 메시지
    assert agent_messages[1]["sender"] == "cinematographer"
    assert agent_messages[1]["recipient"] == "director"
    assert agent_messages[1]["message_type"] == "approval"
    assert "close-up으로 변경했습니다" in agent_messages[1]["content"]


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_agent_with_message", new_callable=AsyncMock)
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_multiple_agent_interactions(
    mock_run_production,
    mock_run_agent,
    mock_production_results,
):
    """Director가 여러 Production Agent와 순차적으로 소통한다."""
    # Step 1: revise_cinematographer → approve
    mock_run_production.side_effect = [
        {
            "observe": "시각 디자인 개선 필요",
            "think": "cinematographer 수정 필요",
            "act": "revise_cinematographer",
            "feedback": "시각 디자인을 개선하세요",
        },
        {
            "observe": "모든 요소가 조화롭다",
            "think": "승인 가능",
            "act": "approve",
        },
    ]

    # Agent 응답
    mock_run_agent.return_value = (
        {"scenes": []},
        {
            "sender": "cinematographer",
            "recipient": "director",
            "content": "시각 디자인을 개선했습니다",
            "message_type": "approval",
        },
    )

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    result = await director_node(state, {})

    # 2 스텝 실행 (revise → approve)
    assert len(result["director_reasoning_steps"]) == 2
    assert result["director_decision"] == "approve"

    # Agent 메시지 2개 (Director → Agent, Agent → Director)
    assert len(result["agent_messages"]) == 2


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_agent_with_message", new_callable=AsyncMock)
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_agent_error_handling(
    mock_run_production,
    mock_run_agent,
    mock_production_results,
):
    """Agent 실행 실패 시에도 Director는 계속 진행한다."""
    mock_run_production.side_effect = [
        {
            "observe": "개선 필요",
            "think": "수정 필요",
            "act": "revise_tts",
            "feedback": "음성 디자인을 개선하세요",
        },
        {
            "observe": "승인",
            "think": "완료",
            "act": "approve",
        },
    ]

    # Agent 실행 실패
    mock_run_agent.side_effect = Exception("TTS Designer 에러")

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    result = await director_node(state, {})

    # 에러에도 불구하고 2 스텝 실행됨
    assert len(result["director_reasoning_steps"]) == 2
    # Agent 메시지는 Director의 피드백만 포함 (응답 없음)
    assert len(result["agent_messages"]) == 1
    assert result["agent_messages"][0]["sender"] == "director"


# ── Phase 11-P3: visual_qc_result → Director template_vars ──


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_visual_qc_result_in_template_vars(mock_run, mock_production_results):
    """visual_qc_result가 template_vars에 포함된다."""
    captured_vars = []

    async def capture_and_approve(*args, **kwargs):
        captured_vars.append(dict(kwargs["template_vars"]))
        return {"observe": "QC 경고 확인", "think": "승인 가능", "act": "approve"}

    mock_run.side_effect = capture_and_approve

    qc = {"ok": False, "issues": ["Scene 0→1 동일 gaze 반복: looking_at_viewer"], "checks": {}}
    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "visual_qc_result": qc,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    await director_node(state, {})

    assert len(captured_vars) == 1
    assert captured_vars[0]["visual_qc_result"] == qc
    assert captured_vars[0]["visual_qc_result"]["ok"] is False


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_visual_qc_result_none(mock_run, mock_production_results):
    """visual_qc_result=None 시 정상 동작."""
    mock_run.return_value = {"observe": "정상", "think": "승인", "act": "approve"}

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    result = await director_node(state, {})
    assert result["director_decision"] == "approve"


# ── BUG 1: 인라인 수정 결과 전파 테스트 ────────────────


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_agent_with_message", new_callable=AsyncMock)
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_inline_revision_result_propagated(
    mock_run_production,
    mock_run_agent,
    mock_production_results,
):
    """인라인 수정 결과가 State에 반영된다 (BUG 1 수정 검증)."""
    mock_run_production.side_effect = [
        {
            "observe": "시각 디자인 부족",
            "think": "카메라 변경 필요",
            "act": "revise_cinematographer",
            "feedback": "카메라를 close-up으로 변경",
        },
        {
            "observe": "수정 완료 확인",
            "think": "승인 가능",
            "act": "approve",
        },
    ]

    updated_cinema = {"scenes": [{"order": 1, "camera": "close-up", "visual_tags": ["smile"]}]}
    mock_run_agent.return_value = (
        updated_cinema,
        {
            "sender": "cinematographer",
            "recipient": "director",
            "content": "수정 완료",
            "message_type": "approval",
        },
    )

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    result = await director_node(state, {})

    # 핵심 검증: 수정된 cinematographer_result가 반환 dict에 포함
    assert "cinematographer_result" in result
    assert result["cinematographer_result"] == updated_cinema
    # 수정되지 않은 에이전트 결과는 포함되지 않음
    assert "tts_designer_result" not in result
    assert "sound_designer_result" not in result


# ── BUG 2: feedback 기록 테스트 ────────────────


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_agent_with_message", new_callable=AsyncMock)
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_feedback_in_reasoning_steps(
    mock_run_production,
    mock_run_agent,
    mock_production_results,
):
    """feedback이 reasoning_steps에 기록된다 (BUG 2 수정 검증)."""
    mock_run_production.side_effect = [
        {
            "observe": "음성 톤 불일치",
            "think": "TTS 수정 필요",
            "act": "revise_tts",
            "feedback": "씬 2의 톤을 더 밝게 변경하세요",
        },
        {
            "observe": "수정 확인",
            "think": "승인",
            "act": "approve",
        },
    ]

    mock_run_agent.return_value = (
        {"tts_designs": []},
        {
            "sender": "tts_designer",
            "recipient": "director",
            "content": "수정 완료",
            "message_type": "approval",
        },
    )

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    result = await director_node(state, {})

    steps = result["director_reasoning_steps"]
    assert len(steps) == 2
    # Step 1: revise → feedback 기록됨
    assert steps[0]["feedback"] == "씬 2의 톤을 더 밝게 변경하세요"
    # Step 2: approve → feedback 빈 문자열
    assert steps[1]["feedback"] == ""


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_agent_with_message", new_callable=AsyncMock)
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_previous_feedback_in_template_vars(
    mock_run,
    mock_run_agent,
    mock_production_results,
):
    """이전 step의 feedback이 다음 step의 template_vars에 전달된다."""
    captured_vars = []

    async def capture_and_return(*args, **kwargs):
        captured_vars.append(list(kwargs["template_vars"].get("previous_steps", [])))
        if len(captured_vars) == 1:
            return {
                "observe": "Step 1 관찰",
                "think": "수정 필요",
                "act": "revise_cinematographer",
                "feedback": "시각 구성 개선 필요",
            }
        return {
            "observe": "Step 2 관찰",
            "think": "승인",
            "act": "approve",
        }

    mock_run.side_effect = capture_and_return
    mock_run_agent.return_value = (
        {"scenes": []},
        {"sender": "cinematographer", "recipient": "director", "content": "완료", "message_type": "approval"},
    )

    state: ScriptState = {  # type: ignore[typeddict-item]
        **mock_production_results,
        "director_revision_count": 0,
        "revision_count": 0,
        "concept_regen_count": 0,
    }

    await director_node(state, {})

    # 두 번째 호출 시 previous_steps에 feedback 포함
    assert len(captured_vars) == 2
    assert len(captured_vars[1]) == 1
    assert captured_vars[1][0]["feedback"] == "시각 구성 개선 필요"
