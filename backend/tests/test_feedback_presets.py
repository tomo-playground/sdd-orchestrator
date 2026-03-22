"""Phase 9-5D: Interactive Feedback 백엔드 테스트.

피드백 프리셋, concept_gate 3-action, 라우팅, 엔드포인트를 검증한다.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from config_pipelines import FEEDBACK_PRESETS, LANGGRAPH_MAX_CONCEPT_REGEN
from routers.scripts import _resolve_feedback_preset
from services.agent.routing import route_after_concept_gate

# -- _resolve_feedback_preset 테스트 --


def test_resolve_feedback_preset_hook_boost():
    """hook_boost 프리셋이 올바른 피드백 텍스트를 반환."""
    result = _resolve_feedback_preset("hook_boost", None)
    assert result == FEEDBACK_PRESETS["hook_boost"]["feedback"]
    assert "Hook" in result


def test_resolve_feedback_preset_tone_change_with_param():
    """tone_change 프리셋에 파라미터 치환이 올바르게 동작."""
    result = _resolve_feedback_preset("tone_change", {"tone": "유머러스"})
    assert "유머러스" in result
    assert "{tone}" not in result


def test_resolve_feedback_preset_unknown():
    """존재하지 않는 프리셋 ID는 빈 문자열 반환."""
    result = _resolve_feedback_preset("nonexistent_preset", None)
    assert result == ""


def test_resolve_feedback_preset_no_preset():
    """빈 문자열 프리셋 ID는 빈 문자열 반환."""
    result = _resolve_feedback_preset("", None)
    assert result == ""


# -- route_after_concept_gate 테스트 --


def test_route_after_concept_gate_select():
    """concept_action='select' → 'location_planner' 라우팅 (Phase 30-P-6)."""
    state = {"concept_action": "select"}
    assert route_after_concept_gate(state) == "location_planner"


def test_route_after_concept_gate_regenerate():
    """concept_action='regenerate' → 'critic' 라우팅."""
    state = {"concept_action": "regenerate"}
    assert route_after_concept_gate(state) == "critic"


# -- concept_gate 노드 3-action 테스트 --


@pytest.fixture
def critic_result_fixture():
    """테스트용 critic_result."""
    return {
        "selected_concept": {"title": "기본 컨셉"},
        "candidates": [
            {"title": "컨셉 A", "concept": "A 설명"},
            {"title": "컨셉 B", "concept": "B 설명"},
            {"title": "컨셉 C", "concept": "C 설명"},
        ],
        "evaluation": {"best_score": 0.8},
    }


@pytest.mark.asyncio
@patch("services.agent.nodes.concept_gate.interrupt")
async def test_concept_gate_regenerate_returns(mock_interrupt, critic_result_fixture):
    """action='regenerate' → critic_result=None, concept_action='regenerate', count 증가."""
    mock_interrupt.return_value = {"action": "regenerate"}
    from services.agent.nodes.concept_gate import concept_gate_node

    state = {"interaction_mode": "guided", "critic_result": critic_result_fixture, "concept_regen_count": 0}
    result = await concept_gate_node(state)

    assert result["critic_result"] is None
    assert result["concept_action"] == "regenerate"
    assert result["concept_regen_count"] == 1


@pytest.mark.asyncio
@patch("services.agent.nodes.concept_gate.interrupt")
async def test_concept_gate_custom_concept_returns(mock_interrupt, critic_result_fixture):
    """action='custom_concept' → synthetic concept이 selected_concept에 주입."""
    custom = {"title": "사용자 커스텀", "concept": "직접 입력한 컨셉"}
    mock_interrupt.return_value = {"action": "custom_concept", "custom_concept": custom}
    from services.agent.nodes.concept_gate import concept_gate_node

    state = {"interaction_mode": "guided", "critic_result": critic_result_fixture}
    result = await concept_gate_node(state)

    assert result["concept_action"] == "select"
    assert result["critic_result"]["selected_concept"] == custom


@pytest.mark.asyncio
@patch("services.agent.nodes.concept_gate.interrupt")
async def test_concept_gate_max_regen_forces_select(mock_interrupt, critic_result_fixture):
    """concept_regen_count >= max 시 regenerate가 강제로 select 처리."""
    mock_interrupt.return_value = {"action": "regenerate"}
    from services.agent.nodes.concept_gate import concept_gate_node

    state = {
        "interaction_mode": "guided",
        "critic_result": critic_result_fixture,
        "concept_regen_count": LANGGRAPH_MAX_CONCEPT_REGEN,
    }
    result = await concept_gate_node(state)

    assert result["concept_action"] == "select"
    assert "critic_result" not in result  # critic_result을 None으로 설정하지 않음


# -- GET /scripts/feedback-presets 엔드포인트 테스트 --


@pytest.mark.asyncio
async def test_feedback_presets_endpoint():
    """GET /scripts/feedback-presets가 4개 프리셋을 반환."""
    from httpx import ASGITransport, AsyncClient

    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/scripts/feedback-presets")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["presets"]) == 4
    ids = {p["id"] for p in data["presets"]}
    assert ids == {"hook_boost", "more_dramatic", "tone_change", "shorten"}
    # tone_change에 param_options 존재
    tone = next(p for p in data["presets"] if p["id"] == "tone_change")
    assert tone["has_params"] is True
    assert "tone" in tone["param_options"]
