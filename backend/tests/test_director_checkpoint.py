"""Director Checkpoint 노드 + 라우팅 단위 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.agent.llm_models import DirectorCheckpointOutput, validate_with_model
from services.agent.nodes.director_checkpoint import director_checkpoint_node
from services.agent.routing import route_after_director_checkpoint

# -- Validation 테스트 (Pydantic 모델 사용) --


def test_validate_checkpoint_proceed():
    """proceed 응답 검증 통과."""
    result = {"decision": "proceed", "score": 0.85, "reasoning": "품질 충분"}
    assert validate_with_model(DirectorCheckpointOutput, result).ok is True


def test_validate_checkpoint_revise():
    """revise 응답 + feedback 검증 통과."""
    result = {
        "decision": "revise",
        "score": 0.5,
        "reasoning": "Hook이 약함",
        "feedback": "첫 씬 Hook 강화 필요",
    }
    assert validate_with_model(DirectorCheckpointOutput, result).ok is True


def test_validate_checkpoint_revise_missing_feedback():
    """revise인데 feedback 없으면 실패."""
    result = {"decision": "revise", "score": 0.5, "reasoning": "Hook이 약함"}
    qc = validate_with_model(DirectorCheckpointOutput, result)
    assert qc.ok is False
    assert any("feedback" in issue for issue in qc.issues)


def test_validate_checkpoint_invalid_decision():
    """잘못된 decision 값 실패."""
    result = {"decision": "invalid", "score": 0.5, "reasoning": "이유"}
    assert validate_with_model(DirectorCheckpointOutput, result).ok is False


def test_validate_checkpoint_not_dict():
    """dict가 아닌 응답은 실패."""
    assert validate_with_model(DirectorCheckpointOutput, "string").ok is False


# -- 노드 테스트 --


@pytest.mark.asyncio
@patch("services.agent.nodes.director_checkpoint.run_production_step", new_callable=AsyncMock)
async def test_checkpoint_node_proceed(mock_run):
    """proceed 결정 시 정상 반환."""
    mock_run.return_value = {
        "decision": "proceed",
        "score": 0.8,
        "reasoning": "충분한 품질",
    }

    state = {
        "topic": "테스트",
        "mode": "full",
        "duration": 30,
        "director_plan": {"creative_goal": "목표"},
        "draft_scenes": [{"script": "씬 1"}],
        "director_checkpoint_revision_count": 0,
    }
    result = await director_checkpoint_node(state)

    assert result["director_checkpoint_decision"] == "proceed"
    assert result["director_checkpoint_score"] == 0.8
    # proceed 시 revision count 증가 없음
    assert result["director_checkpoint_revision_count"] == 0


@pytest.mark.asyncio
@patch("services.agent.nodes.director_checkpoint.run_production_step", new_callable=AsyncMock)
async def test_checkpoint_node_revise(mock_run):
    """revise 결정 시 feedback + revision count 증가."""
    mock_run.return_value = {
        "decision": "revise",
        "score": 0.4,
        "reasoning": "Hook 부족",
        "feedback": "첫 씬 강화 필요",
    }

    state = {
        "topic": "테스트",
        "mode": "full",
        "duration": 30,
        "director_plan": None,
        "draft_scenes": [],
        "director_checkpoint_revision_count": 0,
    }
    result = await director_checkpoint_node(state)

    assert result["director_checkpoint_decision"] == "revise"
    assert result["director_checkpoint_revision_count"] == 1
    assert result["revision_feedback"] == "첫 씬 강화 필요"


@pytest.mark.asyncio
@patch("services.agent.nodes.director_checkpoint.run_production_step", new_callable=AsyncMock)
async def test_checkpoint_node_failure_auto_proceed(mock_run):
    """Gemini 실패 시 자동 통과 (proceed)."""
    mock_run.side_effect = RuntimeError("Gemini 실패")

    state = {"topic": "실패", "mode": "full", "duration": 30}
    result = await director_checkpoint_node(state)

    assert result["director_checkpoint_decision"] == "proceed"


# -- 라우팅 테스트 --


def test_route_checkpoint_proceed():
    """proceed → cinematographer."""
    state = {"director_checkpoint_decision": "proceed"}
    assert route_after_director_checkpoint(state) == "cinematographer"


def test_route_checkpoint_revise():
    """revise (횟수 미달) → writer (재생성)."""
    state = {
        "director_checkpoint_decision": "revise",
        "director_checkpoint_revision_count": 0,
    }
    assert route_after_director_checkpoint(state) == "writer"


def test_route_checkpoint_revise_max():
    """revise 최대 횟수 도달 → cinematographer 강제 통과."""
    state = {
        "director_checkpoint_decision": "revise",
        "director_checkpoint_revision_count": 3,  # >= MAX(3)
    }
    assert route_after_director_checkpoint(state) == "cinematographer"


def test_route_checkpoint_error():
    """에러 상태 → finalize."""
    state = {"error": "이전 노드 에러", "director_checkpoint_decision": "proceed"}
    assert route_after_director_checkpoint(state) == "finalize"


def test_route_checkpoint_default():
    """decision 미설정 시 기본값 proceed → cinematographer."""
    state = {}
    assert route_after_director_checkpoint(state) == "cinematographer"


# -- Checkpoint → Writer 재생성 흐름 테스트 --


def test_route_checkpoint_revise_goes_to_writer_not_revise():
    """checkpoint revise는 revise 노드가 아닌 writer로 직접 라우팅한다."""
    state = {
        "director_checkpoint_decision": "revise",
        "director_checkpoint_revision_count": 0,
    }
    result = route_after_director_checkpoint(state)
    assert result == "writer", "checkpoint revise는 writer로 가야 함 (revise 노드 아님)"


@pytest.mark.asyncio
@patch("services.agent.nodes.director_checkpoint.run_production_step", new_callable=AsyncMock)
async def test_checkpoint_revise_sets_revision_feedback(mock_run):
    """revise 결정 시 revision_feedback이 설정되어 writer에 전달될 수 있다."""
    feedback_text = "첫 씬 Hook이 약하고 감정 곡선이 평탄합니다"
    mock_run.return_value = {
        "decision": "revise",
        "score": 0.4,
        "reasoning": "Hook 부족",
        "feedback": feedback_text,
    }

    state = {
        "topic": "테스트",
        "mode": "full",
        "duration": 30,
        "director_plan": {"creative_goal": "감동"},
        "draft_scenes": [{"script": "씬 1"}],
        "director_checkpoint_revision_count": 0,
    }
    result = await director_checkpoint_node(state)

    assert result["revision_feedback"] == feedback_text
    assert result["director_checkpoint_feedback"] == feedback_text


@pytest.mark.asyncio
@patch("services.agent.nodes.director_checkpoint.run_production_step", new_callable=AsyncMock)
async def test_checkpoint_proceed_no_revision_feedback(mock_run):
    """proceed 결정 시 revision_feedback이 설정되지 않는다."""
    mock_run.return_value = {
        "decision": "proceed",
        "score": 0.9,
        "reasoning": "우수",
    }

    state = {
        "topic": "테스트",
        "mode": "full",
        "duration": 30,
        "director_checkpoint_revision_count": 0,
    }
    result = await director_checkpoint_node(state)

    assert "revision_feedback" not in result


def test_validate_checkpoint_missing_score():
    """score 없으면 실패."""
    result = {"decision": "proceed", "reasoning": "이유"}
    assert validate_with_model(DirectorCheckpointOutput, result).ok is False


def test_validate_checkpoint_missing_reasoning():
    """reasoning 없으면 실패."""
    result = {"decision": "proceed", "score": 0.8}
    assert validate_with_model(DirectorCheckpointOutput, result).ok is False


# -- Score-Based Decision Override 테스트 --


@pytest.mark.asyncio
@patch("services.agent.nodes.director_checkpoint.run_production_step", new_callable=AsyncMock)
async def test_checkpoint_override_proceed_to_revise_low_score(mock_run):
    """Gemini proceed인데 score < 0.4 → revise로 override."""
    mock_run.return_value = {
        "decision": "proceed",
        "score": 0.3,
        "reasoning": "대충 괜찮음",
    }

    state = {
        "topic": "테스트",
        "mode": "full",
        "duration": 30,
        "director_plan": {"creative_goal": "목표"},
        "draft_scenes": [{"script": "씬 1"}],
        "director_checkpoint_revision_count": 0,
    }
    result = await director_checkpoint_node(state)

    assert result["director_checkpoint_decision"] == "revise"
    assert result["director_checkpoint_score"] == 0.3
    assert result["director_checkpoint_revision_count"] == 1
    assert "revision_feedback" in result


@pytest.mark.asyncio
@patch("services.agent.nodes.director_checkpoint.run_production_step", new_callable=AsyncMock)
async def test_checkpoint_override_revise_to_proceed_high_score(mock_run):
    """Gemini revise인데 score >= 0.85 → proceed로 override."""
    mock_run.return_value = {
        "decision": "revise",
        "score": 0.9,
        "reasoning": "약간 아쉬움",
        "feedback": "조금 더 개선 필요",
    }

    state = {
        "topic": "테스트",
        "mode": "full",
        "duration": 30,
        "director_plan": {"creative_goal": "목표"},
        "draft_scenes": [{"script": "씬 1"}],
        "director_checkpoint_revision_count": 0,
    }
    result = await director_checkpoint_node(state)

    assert result["director_checkpoint_decision"] == "proceed"
    assert result["director_checkpoint_score"] == 0.9
    assert result["director_checkpoint_revision_count"] == 0
    assert "revision_feedback" not in result


@pytest.mark.asyncio
@patch("services.agent.nodes.director_checkpoint.run_production_step", new_callable=AsyncMock)
async def test_checkpoint_no_override_normal_score(mock_run):
    """score가 0.4~0.85 범위면 override 없음."""
    mock_run.return_value = {
        "decision": "revise",
        "score": 0.5,
        "reasoning": "Hook 부족",
        "feedback": "첫 씬 강화",
    }

    state = {
        "topic": "테스트",
        "mode": "full",
        "duration": 30,
        "director_plan": None,
        "draft_scenes": [],
        "director_checkpoint_revision_count": 0,
    }
    result = await director_checkpoint_node(state)

    assert result["director_checkpoint_decision"] == "revise"
    assert result["director_checkpoint_score"] == 0.5
    assert result["revision_feedback"] == "첫 씬 강화"


@pytest.mark.asyncio
@patch("services.agent.nodes.director_checkpoint.run_production_step", new_callable=AsyncMock)
async def test_checkpoint_override_proceed_low_score_generates_feedback(mock_run):
    """proceed→revise override 시 feedback이 없으면 기본 피드백 생성."""
    mock_run.return_value = {
        "decision": "proceed",
        "score": 0.2,
        "reasoning": "ok",
    }

    state = {
        "topic": "테스트",
        "mode": "full",
        "duration": 30,
        "director_checkpoint_revision_count": 0,
    }
    result = await director_checkpoint_node(state)

    assert result["director_checkpoint_decision"] == "revise"
    assert "구조 재작성 필요" in result["revision_feedback"]
