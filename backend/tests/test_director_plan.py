"""Director Plan 노드 단위 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.agent.llm_models import DirectorPlanOutput, validate_with_model
from services.agent.nodes.director_plan import director_plan_node

# -- Validation 테스트 (Pydantic 모델 사용) --


def test_validate_plan_success():
    """정상 응답 검증 통과."""
    result = {
        "creative_goal": "시청자의 호기심을 자극하는 영상",
        "target_emotion": "놀라움",
        "quality_criteria": ["Hook 3초 이내", "감정 전환 2회 이상"],
        "risk_areas": ["자극적 소재 주의"],
        "style_direction": "밝고 경쾌한 톤",
    }
    assert validate_with_model(DirectorPlanOutput, result).ok is True


def test_validate_plan_missing_fields():
    """필수 필드 누락 시 실패."""
    result = {"creative_goal": "목표만 있음"}
    qc = validate_with_model(DirectorPlanOutput, result)
    assert qc.ok is False
    assert len(qc.issues) > 0


def test_validate_plan_not_dict():
    """dict가 아닌 응답은 실패."""
    assert validate_with_model(DirectorPlanOutput, "not a dict").ok is False
    assert validate_with_model(DirectorPlanOutput, []).ok is False


def test_validate_plan_empty_criteria():
    """quality_criteria가 빈 리스트이면 실패."""
    result = {
        "creative_goal": "목표",
        "target_emotion": "감정",
        "quality_criteria": [],
    }
    assert validate_with_model(DirectorPlanOutput, result).ok is False


# -- 노드 테스트 --


@pytest.mark.asyncio
@patch("services.agent.nodes.director_plan.run_production_step", new_callable=AsyncMock)
async def test_director_plan_node_success(mock_run):
    """정상 실행 시 director_plan 반환."""
    mock_run.return_value = {
        "creative_goal": "감동적인 영상 제작",
        "target_emotion": "감동",
        "quality_criteria": ["Hook 강화", "감정 곡선"],
        "risk_areas": [],
        "style_direction": "따뜻한 톤",
    }

    state = {"topic": "테스트 주제", "duration": 30}
    result = await director_plan_node(state)

    assert result["director_plan"] is not None
    assert result["director_plan"]["creative_goal"] == "감동적인 영상 제작"
    assert len(result["director_plan"]["quality_criteria"]) == 2


@pytest.mark.asyncio
@patch("services.agent.nodes.director_plan.run_production_step", new_callable=AsyncMock)
async def test_director_plan_node_failure_graceful(mock_run):
    """Gemini 실패 시 graceful degradation — director_plan: None."""
    mock_run.side_effect = RuntimeError("Gemini API 실패")

    state = {"topic": "실패 테스트", "duration": 30}
    result = await director_plan_node(state)

    assert result["director_plan"] is None


@pytest.mark.asyncio
@patch("services.agent.nodes.director_plan.run_production_step", new_callable=AsyncMock)
async def test_director_plan_node_partial_response(mock_run):
    """일부 필드만 반환된 경우에도 안전하게 처리."""
    mock_run.return_value = {
        "creative_goal": "목표만 있음",
        "target_emotion": "감정",
        "quality_criteria": ["기준 1"],
    }

    state = {"topic": "부분 응답", "duration": 30}
    result = await director_plan_node(state)

    plan = result["director_plan"]
    assert plan["creative_goal"] == "목표만 있음"
    assert plan["risk_areas"] == []
    assert plan["style_direction"] == ""


# -- 추가 Validation 테스트 --


def test_validate_plan_criteria_not_list():
    """quality_criteria가 리스트가 아니면 실패."""
    result = {
        "creative_goal": "목표",
        "target_emotion": "감정",
        "quality_criteria": "문자열",
    }
    assert validate_with_model(DirectorPlanOutput, result).ok is False


def test_validate_plan_missing_creative_goal():
    """creative_goal이 빈 문자열이면 실패."""
    result = {
        "creative_goal": "",
        "target_emotion": "감정",
        "quality_criteria": ["기준"],
    }
    assert validate_with_model(DirectorPlanOutput, result).ok is False


def test_validate_plan_all_missing():
    """모든 필수 필드 누락 시 모두 감지."""
    qc = validate_with_model(DirectorPlanOutput, {})
    assert qc.ok is False
    assert len(qc.issues) > 0


# -- Director Plan이 후속 노드에 전파되는지 검증 --


@pytest.mark.asyncio
@patch("services.agent.nodes.director_plan.run_production_step", new_callable=AsyncMock)
async def test_director_plan_populates_all_fields(mock_run):
    """모든 필드가 정상적으로 채워진다."""
    mock_run.return_value = {
        "creative_goal": "감동 영상",
        "target_emotion": "향수",
        "quality_criteria": ["Hook 3초", "감정 전환", "일관성"],
        "risk_areas": ["민감 소재"],
        "style_direction": "따뜻한 파스텔톤",
    }

    state = {"topic": "여행", "duration": 30}
    result = await director_plan_node(state)

    plan = result["director_plan"]
    assert plan["creative_goal"] == "감동 영상"
    assert plan["target_emotion"] == "향수"
    assert len(plan["quality_criteria"]) == 3
    assert plan["risk_areas"] == ["민감 소재"]
    assert plan["style_direction"] == "따뜻한 파스텔톤"


@pytest.mark.asyncio
@patch("services.agent.nodes.director_plan.run_production_step", new_callable=AsyncMock)
async def test_director_plan_none_does_not_set_error(mock_run):
    """실패해도 error 필드를 설정하지 않는다 (graceful)."""
    mock_run.side_effect = RuntimeError("타임아웃")

    state = {"topic": "실패", "duration": 30}
    result = await director_plan_node(state)

    assert result["director_plan"] is None
    assert "error" not in result
