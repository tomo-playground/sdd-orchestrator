"""Production 노드 컨텍스트 전달 테스트.

BUG 3: Sound Designer에 writer_plan 전달 (emotional_arc_section 빌더 경유)
BUG 4: TTS Designer/Cinematographer에 director_plan 전달
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.state import ScriptState


def _base_state(**overrides) -> ScriptState:
    """테스트용 기본 ScriptState."""
    state: dict = {
        "cinematographer_result": {"scenes": [{"order": 1, "text": "테스트"}]},
        "critic_result": {"mood_progression": "calm → tense"},
        "duration": 30,
        "language": "Korean",
        "revision_count": 0,
        "concept_regen_count": 0,
        # skip production을 제거해야 노드가 실행됨
        "skip_stages": ["research", "concept", "explain"],
    }
    state.update(overrides)
    return state  # type: ignore[return-value]


# ── BUG 3: Sound Designer writer_plan 전달 ────────────────


@pytest.mark.asyncio
@patch("services.agent.nodes.sound_designer.run_production_step", new_callable=AsyncMock)
async def test_sound_designer_passes_writer_plan(mock_run):
    """writer_plan이 Sound Designer의 emotional_arc_section에 반영된다."""
    from services.agent.nodes.sound_designer import sound_designer_node

    mock_run.return_value = {
        "recommendation": {"prompt": "calm guitar", "mood": "calm", "duration": 30}
    }

    writer_plan = {
        "hook_strategy": "질문으로 시작",
        "emotional_arc": ["curious", "tense", "relieved"],
        "scene_distribution": {"intro": 1, "body": 2, "outro": 1},
    }
    state = _base_state(writer_plan=writer_plan)

    await sound_designer_node(state)

    assert mock_run.call_count == 1
    tv = mock_run.call_args.kwargs["template_vars"]
    # writer_plan은 빌더 함수를 통해 emotional_arc_section으로 변환
    assert "emotional_arc_section" in tv
    assert "curious" in tv["emotional_arc_section"]
    assert "tense" in tv["emotional_arc_section"]
    assert "relieved" in tv["emotional_arc_section"]


@pytest.mark.asyncio
@patch("services.agent.nodes.sound_designer.run_production_step", new_callable=AsyncMock)
async def test_sound_designer_writer_plan_none(mock_run):
    """writer_plan이 None이어도 Sound Designer가 정상 동작한다."""
    from services.agent.nodes.sound_designer import sound_designer_node

    mock_run.return_value = {
        "recommendation": {"prompt": "calm guitar", "mood": "calm", "duration": 30}
    }

    state = _base_state(writer_plan=None)

    result = await sound_designer_node(state)

    assert mock_run.call_count == 1
    tv = mock_run.call_args.kwargs["template_vars"]
    # writer_plan=None → emotional_arc_section은 빈 문자열
    assert tv["emotional_arc_section"] == ""
    assert "sound_designer_result" in result


# ── BUG 4: TTS Designer director_plan 전달 ────────────────


@pytest.mark.asyncio
@patch("services.agent.nodes.tts_designer.run_production_step", new_callable=AsyncMock)
async def test_tts_designer_passes_director_plan(mock_run):
    """director_plan이 TTS Designer의 director_plan_section에 반영된다."""
    from services.agent.nodes.tts_designer import tts_designer_node

    mock_run.return_value = {"tts_designs": [{"scene_id": 1, "voice_design_prompt": "calm"}]}

    director_plan = {
        "creative_goal": "감동적인 쇼츠",
        "target_emotion": "nostalgic",
        "quality_criteria": ["감정 일관성", "톤 통일"],
    }
    state = _base_state(director_plan=director_plan)

    await tts_designer_node(state)

    assert mock_run.call_count == 1
    tv = mock_run.call_args.kwargs["template_vars"]
    # director_plan은 빌더 함수를 통해 director_plan_section으로 변환
    assert "director_plan_section" in tv
    assert "nostalgic" in tv["director_plan_section"]


@pytest.mark.asyncio
@patch("services.agent.nodes.tts_designer.run_production_step", new_callable=AsyncMock)
async def test_tts_designer_passes_writer_plan(mock_run):
    """writer_plan이 TTS Designer의 emotional_arc_section에 반영된다."""
    from services.agent.nodes.tts_designer import tts_designer_node

    mock_run.return_value = {"tts_designs": []}

    writer_plan = {
        "hook_strategy": "감정적 질문",
        "emotional_arc": ["sad", "hopeful", "determined"],
        "scene_distribution": {"intro": 1, "body": 2},
    }
    state = _base_state(writer_plan=writer_plan)

    await tts_designer_node(state)

    tv = mock_run.call_args.kwargs["template_vars"]
    assert "emotional_arc_section" in tv
    assert "sad" in tv["emotional_arc_section"]
    assert "hopeful" in tv["emotional_arc_section"]


@pytest.mark.asyncio
@patch("services.agent.nodes.tts_designer.run_production_step", new_callable=AsyncMock)
async def test_tts_designer_no_plans(mock_run):
    """director_plan/writer_plan 모두 None이어도 정상 동작한다."""
    from services.agent.nodes.tts_designer import tts_designer_node

    mock_run.return_value = {"tts_designs": []}

    state = _base_state(director_plan=None, writer_plan=None)

    result = await tts_designer_node(state)

    tv = mock_run.call_args.kwargs["template_vars"]
    # None → 빈 문자열
    assert tv["director_plan_section"] == ""
    assert tv["emotional_arc_section"] == ""
    assert "tts_designer_result" in result


# ── BUG 4: Cinematographer director_plan 전달 ────────────────


@pytest.mark.asyncio
@patch("services.agent.nodes.cinematographer.validate_visuals")
@patch("services.agent.tools.base.call_with_tools", new_callable=AsyncMock)
@patch("services.agent.langfuse_prompt.compile_prompt")
async def test_cinematographer_passes_director_plan(mock_compile, mock_cwt, mock_qc):
    """director_plan이 Cinematographer의 compile_prompt에 creative_direction_section으로 전달된다."""
    from services.agent.nodes.cinematographer import _run

    mock_compile.return_value = MagicMock(system="sys", user="rendered prompt", langfuse_prompt=None)
    mock_cwt.return_value = (
        '```json\n{"scenes": [{"order": 1, "visual_tags": ["smile"]}]}\n```',
        [],
    )
    mock_qc.return_value = {"ok": True, "issues": [], "checks": {}}

    director_plan = {
        "creative_goal": "강렬한 액션",
        "target_emotion": "excited",
        "quality_criteria": ["역동적 카메라"],
    }
    state = _base_state(
        draft_scenes=[{"order": 1, "text": "test", "duration": 3.0}],
        director_plan=director_plan,
        character_id=None,
        director_feedback=None,
        style="Anime",
        creative_direction={"creative_goal": "강렬한 액션", "target_emotion": "excited"},
    )

    db_mock = MagicMock()

    await _run(state, db_mock)

    # compile_prompt 호출 시 creative_direction_section이 전달되었는지 확인
    compile_kwargs = mock_compile.call_args.kwargs
    assert "creative_direction_section" in compile_kwargs
