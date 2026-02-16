"""Production 노드 단위 테스트 — Gemini를 mock하여 각 노드의 동작을 검증한다."""

from __future__ import annotations

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
        enriched.append({
            **s,
            "camera": "close-up",
            "environment": "classroom",
            "image_prompt": f"{s['image_prompt']}, 1girl, brown_hair, indoors",
        })
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
@patch("services.agent.nodes.cinematographer.run_production_step", new_callable=AsyncMock)
async def test_cinematographer_node(mock_step, mock_scenes):
    """Cinematographer 노드가 올바른 state를 반환한다."""
    from services.agent.nodes.cinematographer import cinematographer_node

    mock_step.return_value = {"scenes": mock_scenes}
    state = {"draft_scenes": mock_scenes, "mode": "full"}
    result = await cinematographer_node(state)
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
    state = {"cinematographer_result": cinema_result, "debate_result": {}, "mode": "full"}
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
    state = {"cinematographer_result": cinema_result, "debate_result": {}, "duration": 30, "mode": "full"}
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


def test_route_after_copyright_auto():
    """auto_approve → finalize."""
    from services.agent.routing import route_after_copyright

    state = {"auto_approve": True}
    assert route_after_copyright(state) == "finalize"


def test_route_after_copyright_manual():
    """auto_approve=False → human_gate."""
    from services.agent.routing import route_after_copyright

    state = {"auto_approve": False}
    assert route_after_copyright(state) == "human_gate"
