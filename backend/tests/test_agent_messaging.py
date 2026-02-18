"""Agent 메시지 라우팅 테스트 (Phase 10-C-2)."""

from __future__ import annotations

import pytest

from services.agent.messages import AgentMessage
from services.agent.nodes._agent_messaging import (
    extract_target_agent_from_decision,
    run_agent_with_message,
)
from services.agent.state import ScriptState

# ── 타겟 에이전트 추출 테스트 ──────────────────────────────


def test_extract_target_agent_approve():
    """approve 결정 시 None 반환."""
    result = extract_target_agent_from_decision("approve")
    assert result is None


def test_extract_target_agent_revise_cinematographer():
    """revise_cinematographer → cinematographer."""
    result = extract_target_agent_from_decision("revise_cinematographer")
    assert result == "cinematographer"


def test_extract_target_agent_revise_tts():
    """revise_tts → tts_designer."""
    result = extract_target_agent_from_decision("revise_tts")
    assert result == "tts_designer"


def test_extract_target_agent_revise_sound():
    """revise_sound → sound_designer."""
    result = extract_target_agent_from_decision("revise_sound")
    assert result == "sound_designer"


def test_extract_target_agent_revise_script():
    """revise_script → None (production agent 아님)."""
    result = extract_target_agent_from_decision("revise_script")
    assert result is None


def test_extract_target_agent_unknown():
    """알 수 없는 decision → None."""
    result = extract_target_agent_from_decision("unknown_decision")
    assert result is None


# ── 에이전트 메시지 실행 테스트 ─────────────────────────────


@pytest.mark.asyncio
async def test_run_agent_with_message_cinematographer(monkeypatch):
    """Cinematographer 에이전트 메시지 실행."""
    # Mock cinematographer_node
    mock_result = {"cinematographer_result": {"scenes": [{"order": 1, "visual_tags": ["updated_tag"]}]}}

    async def mock_cinematographer_node(state, config):
        return mock_result

    monkeypatch.setattr(
        "services.agent.nodes.cinematographer.cinematographer_node",
        mock_cinematographer_node,
    )

    state: ScriptState = {"draft_scenes": [{"order": 1, "text": "Test"}]}
    message: AgentMessage = {
        "sender": "director",
        "recipient": "cinematographer",
        "content": "씬 1의 visual_tags를 수정하세요",
        "message_type": "feedback",
    }

    updated_result, response = await run_agent_with_message(
        target_agent="cinematographer",
        state=state,
        message=message,
        config=None,
    )

    # 결과 검증
    assert updated_result == mock_result["cinematographer_result"]

    # 응답 메시지 검증
    assert response["sender"] == "cinematographer"
    assert response["recipient"] == "director"
    assert response["message_type"] == "approval"
    assert "result" in response.get("metadata", {})


@pytest.mark.asyncio
async def test_run_agent_with_message_tts_designer(monkeypatch):
    """TTS Designer 에이전트 메시지 실행."""
    mock_result = {"tts_designer_result": {"scenes": [{"order": 1, "voice_design": "updated"}]}}

    async def mock_tts_designer_node(state):
        return mock_result

    monkeypatch.setattr(
        "services.agent.nodes.tts_designer.tts_designer_node",
        mock_tts_designer_node,
    )

    state: ScriptState = {"draft_scenes": [{"order": 1, "text": "Test"}]}
    message: AgentMessage = {
        "sender": "director",
        "recipient": "tts_designer",
        "content": "감정 표현을 강화하세요",
        "message_type": "feedback",
    }

    updated_result, response = await run_agent_with_message(
        target_agent="tts_designer",
        state=state,
        message=message,
        config=None,
    )

    assert updated_result == mock_result["tts_designer_result"]
    assert response["sender"] == "tts_designer"


@pytest.mark.asyncio
async def test_run_agent_with_message_invalid_agent():
    """지원하지 않는 에이전트 → ValueError."""
    state: ScriptState = {}
    message: AgentMessage = {
        "sender": "director",
        "recipient": "invalid_agent",
        "content": "Test",
        "message_type": "feedback",
    }

    with pytest.raises(ValueError, match="Unsupported target agent"):
        await run_agent_with_message(
            target_agent="invalid_agent",
            state=state,
            message=message,
            config=None,
        )


@pytest.mark.asyncio
async def test_run_agent_with_message_injects_feedback(monkeypatch):
    """메시지 content가 director_feedback으로 주입되는지 확인."""
    captured_state = None

    async def mock_cinematographer_node(state, config):
        nonlocal captured_state
        captured_state = state
        return {"cinematographer_result": {}}

    monkeypatch.setattr(
        "services.agent.nodes.cinematographer.cinematographer_node",
        mock_cinematographer_node,
    )

    state: ScriptState = {"draft_scenes": []}
    message: AgentMessage = {
        "sender": "director",
        "recipient": "cinematographer",
        "content": "이것은 피드백입니다",
        "message_type": "feedback",
    }

    await run_agent_with_message(
        target_agent="cinematographer",
        state=state,
        message=message,
        config=None,
    )

    # director_feedback가 state에 주입되었는지 확인
    assert captured_state is not None
    assert captured_state["director_feedback"] == "이것은 피드백입니다"
