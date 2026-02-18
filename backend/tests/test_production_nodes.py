"""Production 노드 단위 테스트 — Gemini를 mock하여 각 노드의 동작을 검증한다."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_scenes():
    """cinematographer 입력용 draft scenes."""
    return [
        {"scene_id": 1, "script": "테스트 씬 1", "speaker": "A", "duration": 3, "image_prompt": "smile"},
        {"scene_id": 2, "script": "테스트 씬 2", "speaker": "A", "duration": 3, "image_prompt": "happy"},
    ]


@pytest.fixture
def cinema_result(mock_scenes):
    """cinematographer 출력용 enriched scenes."""
    enriched = []
    for s in mock_scenes:
        enriched.append(
            {
                **s,
                "camera": "close-up",
                "environment": "classroom",
                "image_prompt": f"{s['image_prompt']}, 1girl, brown_hair, indoors",
            }
        )
    return {"scenes": enriched}


# -- _production_utils --


@pytest.mark.asyncio
@patch("services.agent.nodes._production_utils.gemini_client")
@patch("services.agent.nodes._production_utils.template_env")
async def test_run_production_step_success(mock_tenv, mock_gemini):
    """정상 응답 → QC 통과 시 결과를 반환한다."""
    from services.agent.nodes._production_utils import run_production_step

    mock_tenv.get_template.return_value.render.return_value = "prompt"
    mock_response = MagicMock()
    mock_response.text = '{"scenes": [{"image_prompt": "test", "camera": "close-up", "environment": "park"}]}'
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)

    result = await run_production_step(
        template_name="creative/cinematographer.j2",
        template_vars={"scenes": []},
        validate_fn=lambda x: {"ok": True, "issues": [], "checks": {}},
        extract_key="scenes",
        step_name="test_step",
    )
    assert "scenes" in result


@pytest.mark.asyncio
@patch("services.agent.nodes._production_utils.gemini_client")
@patch("services.agent.nodes._production_utils.template_env")
async def test_run_production_step_retry_on_qc_fail(mock_tenv, mock_gemini):
    """QC 실패 → 재시도 후 성공."""
    from services.agent.nodes._production_utils import run_production_step

    mock_tenv.get_template.return_value.render.return_value = "prompt"
    mock_response = MagicMock()
    mock_response.text = '{"scenes": [{"image_prompt": "test"}]}'
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)

    call_count = 0

    def qc_fn(extracted):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"ok": False, "issues": ["missing camera"], "checks": {}}
        return {"ok": True, "issues": [], "checks": {}}

    result = await run_production_step(
        template_name="creative/cinematographer.j2",
        template_vars={"scenes": []},
        validate_fn=qc_fn,
        extract_key="scenes",
        step_name="test_step",
    )
    assert call_count == 2
    assert "scenes" in result


# -- Cinematographer Node --


@pytest.mark.asyncio
@patch("services.agent.tools.base.call_with_tools", new_callable=AsyncMock)
@patch("services.agent.nodes.cinematographer.validate_visuals")
async def test_cinematographer_node(mock_validate, mock_call, mock_scenes):
    """Cinematographer 노드가 올바른 state를 반환한다."""
    from services.agent.nodes.cinematographer import cinematographer_node

    # Tool-Calling 결과 모킹
    mock_call.return_value = (
        f"""```json
{{"scenes": {json.dumps(mock_scenes)}}}
```""",
        [],
    )
    mock_validate.return_value = {"valid": True}

    state = {"draft_scenes": mock_scenes, "mode": "full"}
    config = {"configurable": {"db": AsyncMock()}}

    result = await cinematographer_node(state, config)
    assert "cinematographer_result" in result
    assert result["cinematographer_result"]["scenes"] == mock_scenes


# -- TTS Designer Node --


@pytest.mark.asyncio
@patch("services.agent.nodes.tts_designer.run_production_step", new_callable=AsyncMock)
async def test_tts_designer_node(mock_step, cinema_result):
    """TTS Designer 노드가 올바른 state를 반환한다."""
    from services.agent.nodes.tts_designer import tts_designer_node

    tts_result = {"tts_designs": [{"scene_id": 1, "voice_design_prompt": "calm"}]}
    mock_step.return_value = tts_result
    state = {"cinematographer_result": cinema_result, "critic_result": {}, "mode": "full"}
    result = await tts_designer_node(state)
    assert "tts_designer_result" in result


# -- Sound Designer Node --


@pytest.mark.asyncio
@patch("services.agent.nodes.sound_designer.run_production_step", new_callable=AsyncMock)
async def test_sound_designer_node(mock_step, cinema_result):
    """Sound Designer 노드가 올바른 state를 반환한다."""
    from services.agent.nodes.sound_designer import sound_designer_node

    sound_result = {"recommendation": {"prompt": "soft piano", "mood": "calm", "duration": 30}}
    mock_step.return_value = sound_result
    state = {"cinematographer_result": cinema_result, "critic_result": {}, "duration": 30, "mode": "full"}
    result = await sound_designer_node(state)
    assert "sound_designer_result" in result


# -- Copyright Reviewer Node --


@pytest.mark.asyncio
@patch("services.agent.nodes.copyright_reviewer.run_production_step", new_callable=AsyncMock)
async def test_copyright_reviewer_node(mock_step, cinema_result):
    """Copyright Reviewer 노드가 올바른 state를 반환한다."""
    from services.agent.nodes.copyright_reviewer import copyright_reviewer_node

    cr_result = {"overall": "PASS", "checks": [{"type": "script_originality", "status": "PASS"}]}
    mock_step.return_value = cr_result
    state = {"cinematographer_result": cinema_result, "mode": "full"}
    result = await copyright_reviewer_node(state)
    assert result["copyright_reviewer_result"]["overall"] == "PASS"


@pytest.mark.asyncio
@patch("services.agent.nodes.copyright_reviewer.run_production_step", new_callable=AsyncMock)
async def test_copyright_reviewer_fallback(mock_step, cinema_result):
    """Copyright Reviewer 실패 시 fallback PASS를 반환한다."""
    from services.agent.nodes.copyright_reviewer import copyright_reviewer_node

    mock_step.side_effect = RuntimeError("API error")
    state = {"cinematographer_result": cinema_result, "mode": "full"}
    result = await copyright_reviewer_node(state)
    assert result["copyright_reviewer_result"]["overall"] == "PASS"
    assert result["copyright_reviewer_result"]["confidence"] == 0.0


# -- Director Node --


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_node_approve(mock_step):
    """Director 노드가 approve 결과를 반환한다 (Phase 10-A ReAct)."""
    from services.agent.nodes.director import director_node

    # Phase 10-A: ReAct 형식 응답
    mock_step.return_value = {
        "observe": "모든 Production 요소를 검토했습니다.",
        "think": "Visual-Voice 조화가 잘 이루어지고 IP 문제도 없습니다.",
        "act": "approve",
        "feedback": "모든 요소가 잘 조화됩니다.",
    }
    state = {
        "cinematographer_result": {"scenes": []},
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": {"recommendation": {}},
        "copyright_reviewer_result": {"overall": "PASS"},
        "director_revision_count": 0,
    }
    result = await director_node(state)
    assert result["director_decision"] == "approve"
    assert result["director_feedback"] == "모든 요소가 잘 조화됩니다."
    assert result["director_revision_count"] == 1
    # Phase 10-A: reasoning_steps 기록 확인
    assert "director_reasoning_steps" in result
    assert len(result["director_reasoning_steps"]) == 1


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_node_revise(mock_step):
    """Director 노드가 revision 요청을 반환한다 (Phase 10-A ReAct)."""
    from services.agent.nodes.director import director_node

    # Phase 10-A: ReAct 형식, 최대 3 스텝까지 revise_* 반환
    mock_step.side_effect = [
        {
            "observe": "카메라 앵글이 모든 씬에서 close-up만 사용되었습니다.",
            "think": "다양한 앵글이 필요합니다.",
            "act": "revise_cinematographer",
            "feedback": "카메라 앵글이 단조롭습니다.",
        },
        {
            "observe": "앵글이 개선되었습니다.",
            "think": "이제 승인 가능합니다.",
            "act": "approve",
        },
    ]
    state = {
        "cinematographer_result": {"scenes": []},
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": {"recommendation": {}},
        "copyright_reviewer_result": {"overall": "PASS"},
        "director_revision_count": 0,
    }
    result = await director_node(state)
    # 첫 스텝에서 revise, 두 번째 스텝에서 approve → 최종 approve
    assert result["director_decision"] == "approve"
    assert result["director_revision_count"] == 1
    # 2개 스텝 기록
    assert len(result["director_reasoning_steps"]) == 2


@pytest.mark.asyncio
@patch("services.agent.nodes.director.run_production_step", new_callable=AsyncMock)
async def test_director_node_error_fallback(mock_step):
    """Director 노드 실패 시 approve fallback."""
    from services.agent.nodes.director import director_node

    mock_step.side_effect = RuntimeError("API error")
    state = {
        "cinematographer_result": {"scenes": []},
        "tts_designer_result": {},
        "sound_designer_result": {},
        "copyright_reviewer_result": {},
        "director_revision_count": 0,
    }
    result = await director_node(state)
    assert result["director_decision"] == "approve"
    assert result["director_revision_count"] == 1


# -- Finalize Node --


@pytest.mark.asyncio
async def test_finalize_quick_passthrough():
    """Quick 모드: draft → final 패스스루."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [{"scene_id": 1, "script": "test"}]
    state = {"mode": "quick", "draft_scenes": scenes}
    result = await finalize_node(state)
    assert result["final_scenes"] == scenes


@pytest.mark.asyncio
async def test_finalize_full_merge():
    """Full 모드: Production 결과 병합."""
    from services.agent.nodes.finalize import finalize_node

    cinema_scenes = [{"scene_id": 1, "script": "test", "camera": "close-up"}]
    tts_designs = [{"scene_id": 1, "voice_design_prompt": "calm"}]
    state = {
        "mode": "full",
        "cinematographer_result": {"scenes": cinema_scenes},
        "tts_designer_result": {"tts_designs": tts_designs},
        "sound_designer_result": {"recommendation": {"prompt": "piano", "mood": "calm", "duration": 30}},
        "copyright_reviewer_result": {"overall": "PASS", "checks": []},
    }
    result = await finalize_node(state)
    final = result["final_scenes"]
    assert len(final) == 1
    assert final[0]["tts_design"]["voice_design_prompt"] == "calm"
    assert final[0]["_sound_recommendation"]["mood"] == "calm"


# -- Routing --


def test_route_after_review_quick():
    """Quick 모드: review 통과 → finalize."""
    from services.agent.routing import route_after_review

    state = {"mode": "quick", "review_result": {"passed": True}}
    assert route_after_review(state) == "finalize"


def test_route_after_review_full():
    """Full 모드: review 통과 → cinematographer."""
    from services.agent.routing import route_after_review

    state = {"mode": "full", "review_result": {"passed": True}}
    assert route_after_review(state) == "cinematographer"


def test_route_after_cinematographer_fanout():
    """cinematographer 이후 → 3개 병렬 fan-out."""
    from services.agent.routing import route_after_cinematographer

    state = {"mode": "full"}
    result = route_after_cinematographer(state)
    assert isinstance(result, list)
    assert set(result) == {"tts_designer", "sound_designer", "copyright_reviewer"}


def test_route_after_cinematographer_error():
    """cinematographer 에러 → finalize."""
    from services.agent.routing import route_after_cinematographer

    state = {"error": "Cinematographer 실패"}
    assert route_after_cinematographer(state) == "finalize"


# -- Director Feedback 전달 테스트 --


@pytest.mark.asyncio
@patch("services.agent.tools.base.call_with_tools", new_callable=AsyncMock)
@patch("services.agent.nodes.cinematographer.validate_visuals")
async def test_cinematographer_passes_director_feedback(mock_validate, mock_call, mock_scenes):
    """Cinematographer가 director_feedback을 프롬프트에 포함한다."""
    from services.agent.nodes.cinematographer import cinematographer_node

    mock_call.return_value = (
        f"""```json
{{"scenes": {json.dumps(mock_scenes)}}}
```""",
        [],
    )
    mock_validate.return_value = {"valid": True}

    state = {"draft_scenes": mock_scenes, "director_feedback": "카메라 다양성 부족"}
    config = {"configurable": {"db": AsyncMock()}}

    await cinematographer_node(state, config)

    # call_with_tools가 호출되었는지 확인
    assert mock_call.called
    # 프롬프트에 director_feedback이 포함되었는지 확인
    call_args = mock_call.call_args
    prompt = call_args[1]["prompt"]
    assert "카메라 다양성 부족" in prompt


@pytest.mark.asyncio
@patch("services.agent.nodes.tts_designer.run_production_step", new_callable=AsyncMock)
async def test_tts_designer_passes_director_feedback(mock_step, cinema_result):
    """TTS Designer가 director_feedback을 template_vars에 전달한다."""
    from services.agent.nodes.tts_designer import tts_designer_node

    mock_step.return_value = {"tts_designs": []}
    state = {"cinematographer_result": cinema_result, "critic_result": {}, "director_feedback": "감정 부족"}
    await tts_designer_node(state)
    call_vars = mock_step.call_args[1]["template_vars"]
    assert call_vars["feedback"] == "감정 부족"


@pytest.mark.asyncio
@patch("services.agent.nodes.sound_designer.run_production_step", new_callable=AsyncMock)
async def test_sound_designer_passes_director_feedback(mock_step, cinema_result):
    """Sound Designer가 director_feedback을 template_vars에 전달한다."""
    from services.agent.nodes.sound_designer import sound_designer_node

    mock_step.return_value = {"recommendation": {"prompt": "test", "mood": "calm", "duration": 30}}
    state = {
        "cinematographer_result": cinema_result,
        "critic_result": {},
        "duration": 30,
        "director_feedback": "BGM 부적절",
    }
    await sound_designer_node(state)
    call_vars = mock_step.call_args[1]["template_vars"]
    assert call_vars["feedback"] == "BGM 부적절"


@pytest.mark.asyncio
@patch("services.agent.nodes.copyright_reviewer.run_production_step", new_callable=AsyncMock)
async def test_copyright_reviewer_passes_director_feedback(mock_step, cinema_result):
    """Copyright Reviewer가 director_feedback을 template_vars에 전달한다."""
    from services.agent.nodes.copyright_reviewer import copyright_reviewer_node

    mock_step.return_value = {"overall": "PASS", "checks": []}
    state = {"cinematographer_result": cinema_result, "director_feedback": "IP 재검토 필요"}
    await copyright_reviewer_node(state)
    call_vars = mock_step.call_args[1]["template_vars"]
    assert call_vars["feedback"] == "IP 재검토 필요"


# -- Fallback 패턴 테스트 --


@pytest.mark.asyncio
@patch("services.agent.nodes.tts_designer.run_production_step", new_callable=AsyncMock)
async def test_tts_designer_fallback(mock_step):
    """TTS Designer 실패 시 fallback 빈 결과를 반환한다."""
    from services.agent.nodes.tts_designer import tts_designer_node

    mock_step.side_effect = RuntimeError("API error")
    state = {"cinematographer_result": {"scenes": []}, "critic_result": {}}
    result = await tts_designer_node(state)
    assert "tts_designer_result" in result
    assert "error" not in result
    assert result["tts_designer_result"]["tts_designs"] == []


@pytest.mark.asyncio
@patch("services.agent.nodes.sound_designer.run_production_step", new_callable=AsyncMock)
async def test_sound_designer_fallback(mock_step):
    """Sound Designer 실패 시 fallback 결과를 반환한다."""
    from services.agent.nodes.sound_designer import sound_designer_node

    mock_step.side_effect = RuntimeError("API error")
    state = {"cinematographer_result": {"scenes": []}, "critic_result": {}, "duration": 30}
    result = await sound_designer_node(state)
    assert "sound_designer_result" in result
    assert "error" not in result
    assert result["sound_designer_result"]["recommendation"]["mood"] == "neutral"


# -- Explain Node 테스트 --


@pytest.mark.asyncio
@patch("services.agent.nodes.explain.run_production_step", new_callable=AsyncMock)
async def test_explain_node_success(mock_step):
    """Explain 노드가 정상 결과를 반환한다."""
    from services.agent.nodes.explain import explain_node

    explain_result = {
        "explanation": {
            "visual_strategy": "테스트 전략",
            "audio_strategy": "테스트 오디오",
            "quality_tradeoffs": "없음",
            "overall_coherence": "좋음",
            "key_decisions": ["결정1", "결정2"],
        },
    }
    mock_step.return_value = explain_result
    state = {"final_scenes": [{"scene_id": 1}], "mode": "full"}
    result = await explain_node(state)
    assert "explanation_result" in result
    assert result["explanation_result"]["explanation"]["visual_strategy"] == "테스트 전략"


@pytest.mark.asyncio
@patch("services.agent.nodes.explain.run_production_step", new_callable=AsyncMock)
async def test_explain_node_error_returns_none(mock_step):
    """Explain 노드 실패 시 None을 반환하고 파이프라인을 차단하지 않는다."""
    from services.agent.nodes.explain import explain_node

    mock_step.side_effect = RuntimeError("API error")
    state = {"final_scenes": [], "mode": "full"}
    result = await explain_node(state)
    assert result["explanation_result"] is None


# -- Revise _build_feedback 테스트 --


def test_build_feedback_includes_director_feedback():
    """_build_feedback이 director_feedback을 포함한다."""
    from services.agent.nodes.revise import _build_feedback

    state = {"director_feedback": "전체적으로 개선 필요"}
    feedback = _build_feedback(state)
    assert "[디렉터 피드백] 전체적으로 개선 필요" in feedback
