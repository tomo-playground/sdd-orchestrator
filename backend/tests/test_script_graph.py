"""LangGraph Script Graph 단위 테스트.

generate_script를 mock하여 Graph 구조와 State 전파를 검증한다.
17노드 그래프 (에러 short-circuit + 병렬 fan-out):
  director_plan → research → critic → concept_gate → writer → review →
  [director_checkpoint] → cinematographer → [tts/sound/copyright 병렬] →
  director → [human_gate] → finalize → [explain] → learn
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.agent.script_graph import build_script_graph
from services.agent.state import ScriptState


@pytest.fixture
def mock_scenes():
    """review 검증을 통과할 수 있는 유효한 씬 데이터."""
    return [
        {
            "scene_id": 1,
            "script": "테스트 씬 1입니다 안녕하세요",
            "speaker": "A",
            "duration": 3,
            "image_prompt": "smile, looking_at_viewer, standing, indoors",
        },
        {
            "scene_id": 2,
            "script": "테스트 씬 2입니다 반갑습니다",
            "speaker": "A",
            "duration": 3,
            "image_prompt": "happy, looking_at_viewer, sitting, outdoors",
        },
        {
            "scene_id": 3,
            "script": "테스트 씬 3입니다 감사합니다",
            "speaker": "A",
            "duration": 3,
            "image_prompt": "smile, cowboy_shot, classroom, indoors",
        },
        {
            "scene_id": 4,
            "script": "테스트 씬 4입니다 좋은 하루요",
            "speaker": "A",
            "duration": 3,
            "image_prompt": "waving, full_body, park, outdoors",
        },
        {
            "scene_id": 5,
            "script": "테스트 씬 5입니다 마지막이에요",
            "speaker": "A",
            "duration": 3,
            "image_prompt": "smile, upper_body, sky, sunset",
        },
    ]


def test_graph_structure():
    """17노드가 모두 Graph에 존재하는지 확인한다."""
    graph = build_script_graph()
    compiled = graph.compile()
    node_names = set(compiled.get_graph().nodes.keys())
    expected = (
        "director_plan",
        "research",
        "critic",
        "concept_gate",
        "writer",
        "review",
        "revise",
        "director_checkpoint",
        "cinematographer",
        "tts_designer",
        "sound_designer",
        "copyright_reviewer",
        "director",
        "human_gate",
        "finalize",
        "explain",
        "learn",
    )
    for node in expected:
        assert node in node_names, f"'{node}' 노드가 그래프에 없음"


@pytest.mark.asyncio
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.get_db_session")
async def test_graph_quick_mode(mock_db_ctx, mock_gen_script, mock_scenes):
    """Quick 모드: writer → review(pass) → finalize → learn → END."""
    mock_gen_script.return_value = {"scenes": mock_scenes, "character_id": 42}

    graph = build_script_graph().compile()
    input_state: ScriptState = {
        "topic": "테스트 주제",
        "character_id": 42,
        "mode": "quick",
        "duration": 10,
    }
    result = await graph.ainvoke(input_state)

    assert result["final_scenes"] is not None
    assert len(result["final_scenes"]) == 5
    assert result["draft_character_id"] == 42


@pytest.mark.asyncio
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.get_db_session")
async def test_graph_state_propagation(mock_db_ctx, mock_gen_script, mock_scenes):
    """draft_scenes == final_scenes (review 통과 시 패스스루)를 확인한다."""
    mock_gen_script.return_value = {"scenes": mock_scenes}

    graph = build_script_graph().compile()
    result = await graph.ainvoke({"topic": "전파 테스트", "mode": "quick", "duration": 10})

    assert result["draft_scenes"] == result["final_scenes"]
    assert result["final_scenes"] == mock_scenes


@pytest.mark.asyncio
@patch("services.agent.nodes.revise.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.revise.get_db_session")
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.get_db_session")
async def test_graph_revise_loop(
    mock_writer_db_ctx,
    mock_writer_gen,
    mock_revise_db_ctx,
    mock_revise_gen,
    mock_scenes,
):
    """Review 실패 → Revise → Review 통과 루프를 검증한다."""
    bad_scenes = [{"script": "짧", "speaker": "A", "duration": 0, "image_prompt": ""}]
    mock_writer_gen.return_value = {"scenes": bad_scenes}
    mock_revise_gen.return_value = {"scenes": mock_scenes}

    graph = build_script_graph().compile()
    result = await graph.ainvoke({"topic": "리비전 테스트", "mode": "quick", "duration": 10})

    assert result["final_scenes"] is not None
    assert result["revision_count"] >= 1


@pytest.mark.asyncio
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.get_db_session")
async def test_graph_error_short_circuit_writer(mock_db_ctx, mock_gen_script):
    """writer 에러 → review 스킵, finalize로 즉시 short-circuit."""
    mock_gen_script.side_effect = Exception("Gemini API 실패")

    graph = build_script_graph().compile()
    result = await graph.ainvoke({"topic": "에러 테스트", "mode": "quick", "duration": 10})

    assert result.get("error") is not None
    assert "Gemini API 실패" in result["error"]
    assert result.get("review_result") is None


def test_routing_fanout_after_cinematographer():
    """cinematographer 이후 → 3개 병렬 fan-out, 에러 시 finalize."""
    from services.agent.routing import route_after_cinematographer

    result = route_after_cinematographer({"mode": "full"})
    assert isinstance(result, list)
    assert set(result) == {"tts_designer", "sound_designer", "copyright_reviewer"}

    assert route_after_cinematographer({"mode": "full", "error": "실패"}) == "finalize"


def test_routing_error_short_circuit_writer():
    """writer 에러 → route_after_writer가 finalize 반환."""
    from services.agent.routing import route_after_writer

    assert route_after_writer({"mode": "quick"}) == "review"
    assert route_after_writer({"mode": "quick", "error": "Gemini API 실패"}) == "finalize"


def test_routing_error_short_circuit_review():
    """review 진입 시 에러 → finalize로 short-circuit."""
    from services.agent.routing import route_after_review

    assert route_after_review({"error": "이전 노드 에러", "mode": "quick"}) == "finalize"
    assert route_after_review({"error": "이전 노드 에러", "mode": "full"}) == "finalize"


# -- Director 라우팅 테스트 --


def test_route_after_director_approve_auto():
    """Director approve + auto_approve → finalize."""
    from services.agent.routing import route_after_director

    state = {"director_decision": "approve", "auto_approve": True}
    assert route_after_director(state) == "finalize"


def test_route_after_director_approve_manual():
    """Director approve + auto_approve=False → human_gate."""
    from services.agent.routing import route_after_director

    state = {"director_decision": "approve", "auto_approve": False}
    assert route_after_director(state) == "human_gate"


def test_route_after_director_revise_cinematographer():
    """Director가 cinematographer 수정을 요청한다."""
    from services.agent.routing import route_after_director

    state = {
        "director_decision": "revise_cinematographer",
        "director_revision_count": 0,
    }
    assert route_after_director(state) == "cinematographer"


def test_route_after_director_revise_tts():
    """Director가 tts_designer 수정을 요청한다."""
    from services.agent.routing import route_after_director

    state = {
        "director_decision": "revise_tts",
        "director_revision_count": 0,
    }
    assert route_after_director(state) == "tts_designer"


def test_route_after_director_revise_sound():
    """Director가 sound_designer 수정을 요청한다."""
    from services.agent.routing import route_after_director

    state = {
        "director_decision": "revise_sound",
        "director_revision_count": 0,
    }
    assert route_after_director(state) == "sound_designer"


def test_route_after_director_revise_script():
    """Director가 스크립트 수정을 요청한다 → revise."""
    from services.agent.routing import route_after_director

    state = {
        "director_decision": "revise_script",
        "director_revision_count": 0,
    }
    assert route_after_director(state) == "revise"


def test_route_after_director_max_revisions():
    """Director revision 최대 횟수 도달 시 human_gate로 강제 통과."""
    from services.agent.routing import route_after_director

    state = {
        "director_decision": "revise_cinematographer",
        "director_revision_count": 1,
    }
    assert route_after_director(state) == "human_gate"


def test_route_after_director_error():
    """에러 상태에서는 finalize로 short-circuit."""
    from services.agent.routing import route_after_director

    state = {"error": "이전 노드 에러", "director_decision": "approve"}
    assert route_after_director(state) == "finalize"


# -- Explain / Finalize 라우팅 테스트 --


def test_route_after_finalize_full():
    """Full 모드: finalize → explain."""
    from services.agent.routing import route_after_finalize

    assert route_after_finalize({"mode": "full"}) == "explain"


def test_route_after_finalize_quick():
    """Quick 모드: finalize → learn (explain 스킵)."""
    from services.agent.routing import route_after_finalize

    assert route_after_finalize({"mode": "quick"}) == "learn"
    assert route_after_finalize({}) == "learn"  # 기본값 quick


def test_graph_17_nodes():
    """17노드가 모두 등록되어 있다."""
    graph = build_script_graph()
    compiled = graph.compile()
    node_names = set(compiled.get_graph().nodes.keys())
    assert "director_plan" in node_names
    assert "director_checkpoint" in node_names
    assert "explain" in node_names
    assert "concept_gate" in node_names
    assert len(node_names - {"__start__", "__end__"}) == 17


# -- Writer Safety Retry 테스트 --


def test_is_safety_error():
    """safety 키워드가 포함된 에러를 정확히 감지한다."""
    from services.agent.nodes.writer import _is_safety_error

    assert _is_safety_error(ValueError("🛡️ Gemini 안전 필터가 콘텐츠를 차단했습니다"))
    assert _is_safety_error(ValueError("Blocked by SAFETY filter"))
    assert _is_safety_error(ValueError("콘텐츠가 차단되었습니다"))
    assert not _is_safety_error(ValueError("Gemini API 타임아웃"))
    assert not _is_safety_error(ValueError("네트워크 에러"))


def test_append_safety_hint():
    """safety 가이드가 description에 추가된다."""
    from services.agent.nodes.writer import _append_safety_hint

    result = _append_safety_hint("원본 설명")
    assert "원본 설명" in result
    assert "안전 가이드" in result
    assert "폭력" in result


@pytest.mark.asyncio
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.get_db_session")
async def test_writer_safety_retry_success(mock_db_ctx, mock_gen_script, mock_scenes):
    """안전 필터 차단 → 재시도 성공."""
    mock_gen_script.side_effect = [
        ValueError("🛡️ Gemini 안전 필터가 콘텐츠를 차단했습니다"),
        {"scenes": mock_scenes, "character_id": 42},
    ]

    graph = build_script_graph().compile()
    result = await graph.ainvoke({"topic": "safety 테스트", "mode": "quick", "duration": 10})

    assert result.get("error") is None
    assert result["final_scenes"] is not None
    assert len(result["final_scenes"]) == 5
    assert mock_gen_script.call_count == 2


@pytest.mark.asyncio
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.get_db_session")
async def test_writer_safety_retry_both_fail(mock_db_ctx, mock_gen_script):
    """안전 필터 2번 연속 차단 → 에러 short-circuit."""
    mock_gen_script.side_effect = [
        ValueError("🛡️ Gemini 안전 필터가 콘텐츠를 차단했습니다"),
        ValueError("🛡️ 재시도도 안전 필터에 차단"),
    ]

    graph = build_script_graph().compile()
    result = await graph.ainvoke({"topic": "이중 safety 실패", "mode": "quick", "duration": 10})

    assert result.get("error") is not None
    assert "차단" in result["error"]
    assert mock_gen_script.call_count == 2


@pytest.mark.asyncio
@patch("services.agent.nodes.writer.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.writer.get_db_session")
async def test_writer_non_safety_error_no_retry(mock_db_ctx, mock_gen_script):
    """non-safety 에러는 재시도 없이 즉시 실패."""
    mock_gen_script.side_effect = Exception("Gemini API 타임아웃")

    graph = build_script_graph().compile()
    result = await graph.ainvoke({"topic": "타임아웃 테스트", "mode": "quick", "duration": 10})

    assert result.get("error") is not None
    assert "타임아웃" in result["error"]
    assert mock_gen_script.call_count == 1  # 재시도 없음


# -- Director Checkpoint → Writer 라우팅 테스트 --


def test_route_review_pass_full_mode_goes_to_checkpoint():
    """Full 모드 review 통과 → director_checkpoint."""
    from services.agent.routing import route_after_review

    state = {
        "mode": "full",
        "review_result": {"passed": True, "errors": []},
    }
    assert route_after_review(state) == "director_checkpoint"


def test_route_checkpoint_revise_goes_to_writer():
    """Checkpoint revise → writer (revise 노드 아님)."""
    from services.agent.routing import route_after_director_checkpoint

    state = {
        "director_checkpoint_decision": "revise",
        "director_checkpoint_revision_count": 0,
    }
    assert route_after_director_checkpoint(state) == "writer"


def test_route_start_full_mode_goes_to_director_plan():
    """Full 모드 START → director_plan."""
    from services.agent.routing import route_after_start

    assert route_after_start({"mode": "full"}) == "director_plan"
    assert route_after_start({"mode": "quick"}) == "writer"
    assert route_after_start({}) == "writer"  # 기본값 quick
